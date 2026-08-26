"""Secure bKash Checkout API integration.

Credentials stay server-side. The browser only receives the bKash paymentID
needed by the official checkout script; create/execute/query calls are made
from this backend and the paid amount is always compared with the order.
"""

import json
import logging
import os
import time
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Blueprint, jsonify, redirect, render_template, request, session
from sqlalchemy import text

from database import SessionLocal
from schema import allow_payment_attempt

bkash_bp = Blueprint("bkash_api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)
_TOKEN = {"value": None, "expires_at": 0.0}


def _user_id():
    value = session.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _money(value):
    try:
        return format(Decimal(str(value or 0)), ".2f")
    except (InvalidOperation, ValueError):
        return "0.00"


def _base_url():
    return os.getenv("BKASH_BASE_URL", "https://checkout.sandbox.bka.sh/v1.2.0-beta").rstrip("/")


def _request(path, method="POST", body=None, retry=True):
    app_key = os.getenv("BKASH_APP_KEY", "").strip()
    if not app_key:
        raise RuntimeError("BKASH_APP_KEY is not configured")
    token = _get_token()
    data = json.dumps(body or {}).encode() if method == "POST" else None
    headers = {"Accept": "application/json", "Authorization": token, "X-App-Key": app_key}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{_base_url()}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if retry and exc.code in {401, 403}:
            _TOKEN.update(value=None, expires_at=0.0)
            return _request(path, method=method, body=body, retry=False)
        raise


def _get_token():
    now = time.time()
    if _TOKEN["value"] and _TOKEN["expires_at"] > now + 60:
        return _TOKEN["value"]
    username = os.getenv("BKASH_USERNAME", "").strip()
    password = os.getenv("BKASH_PASSWORD", "").strip()
    app_key = os.getenv("BKASH_APP_KEY", "").strip()
    app_secret = os.getenv("BKASH_APP_SECRET", "").strip()
    if not all((username, password, app_key, app_secret)):
        raise RuntimeError("bKash credentials are not fully configured")
    body = json.dumps({"app_key": app_key, "app_secret": app_secret}).encode()
    req = Request(
        f"{_base_url()}/checkout/token/grant",
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "username": username, "password": password},
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    token = result.get("id_token")
    if not token:
        raise RuntimeError(f"bKash token grant failed: {result.get('statusMessage', 'unknown error')}")
    expires_in = int(result.get("expires_in") or 3600)
    _TOKEN.update(value=token, expires_at=now + min(expires_in, 3600))
    return token


def _success(result):
    status_code = str(result.get("statusCode", ""))
    transaction_status = str(result.get("transactionStatus", "")).upper()
    return status_code == "0000" and transaction_status in {"COMPLETED", "SUCCESS"}


def _order(order_id, user_id, db):
    return db.execute(text("""SELECT id,order_number,total_amount,currency,status,payment_status
        FROM commerce_orders WHERE id=:order_id AND user_id=:user_id FOR UPDATE"""),
        {"order_id": order_id, "user_id": user_id}).mappings().first()


@bkash_bp.get("/../payment/bkash/<int:order_id>")
def bkash_page(order_id):
    user_id = _user_id()
    if user_id is None:
        return redirect("/login")
    with SessionLocal() as db:
        order = _order(order_id, user_id, db)
    if order is None:
        return jsonify({"error": "Order not found."}), 404
    if order["payment_status"] == "paid":
        return redirect(f"/payment-result/success?order_id={order_id}")
    return render_template(
        "bkash_checkout.html",
        order=order,
        script_url=os.getenv("BKASH_SCRIPT_URL", "").strip(),
    )


@bkash_bp.post("/orders/<int:order_id>/payments/bkash/create")
def create_bkash_payment(order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    if not allow_payment_attempt(request.remote_addr, user_id):
        return jsonify({"error": "Too many payment attempts. Please wait a few minutes and try again."}), 429

    with SessionLocal() as db:
        order = _order(order_id, user_id, db)
        if order is None:
            return jsonify({"error": "Order not found."}), 404
        if order["status"] in {"cancelled", "refunded"} or order["payment_status"] == "paid":
            return jsonify({"error": "This order cannot accept payment."}), 409

        payment = db.execute(text("""SELECT id,transaction_id,status,amount,currency,provider_reference
            FROM payments WHERE order_id=:order_id AND provider='bkash' AND status='initiated'
            ORDER BY id DESC LIMIT 1 FOR UPDATE"""), {"order_id": order_id}).mappings().first()
        if payment is None:
            invoice = f"BK-{order['order_number']}-{uuid4().hex[:8].upper()}"
            payment_id = db.execute(text("""INSERT INTO payments
                (order_id,provider,transaction_id,status,amount,currency,created_at,updated_at)
                VALUES (:order_id,'bkash',:invoice,'initiated',:amount,:currency,NOW(),NOW()) RETURNING id"""),
                {"order_id": order_id, "invoice": invoice, "amount": order["total_amount"],
                 "currency": order["currency"] or "BDT"}).scalar_one()
            payment = {"id": payment_id, "transaction_id": invoice, "status": "initiated",
                       "amount": order["total_amount"], "currency": order["currency"] or "BDT",
                       "provider_reference": None}
            db.execute(text("UPDATE commerce_orders SET payment_status='initiated',updated_at=NOW() WHERE id=:order_id"),
                       {"order_id": order_id})
            db.commit()

        try:
            result = _request("/checkout/payment/create", body={
                "amount": _money(payment["amount"]),
                "currency": str(payment["currency"] or "BDT").upper(),
                "intent": "sale",
                "merchantInvoiceNumber": str(payment["transaction_id"]),
            })
        except Exception:
            logger.exception("bKash create failed order_id=%s", order_id)
            db.rollback()
            return jsonify({"error": "Could not create the bKash payment."}), 502

        payment_id_bkash = str(result.get("paymentID") or "").strip()
        if not payment_id_bkash:
            db.rollback()
            return jsonify({"error": "bKash did not return a paymentID."}), 502
        db.execute(text("UPDATE payments SET provider_reference=:ref,updated_at=NOW() WHERE id=:id"),
                   {"ref": payment_id_bkash, "id": payment["id"]})
        db.commit()

    return jsonify(result)


@bkash_bp.post("/orders/<int:order_id>/payments/bkash/execute")
def execute_bkash_payment(order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    payment_id_bkash = str(body.get("paymentID", "")).strip()
    if not payment_id_bkash or len(payment_id_bkash) > 100:
        return jsonify({"error": "paymentID is required."}), 400

    with SessionLocal() as db:
        payment = db.execute(text("""SELECT p.id,p.order_id,p.status,p.amount,p.currency,p.provider_reference,p.transaction_id
            FROM payments p JOIN commerce_orders o ON o.id=p.order_id
            WHERE p.provider='bkash' AND p.order_id=:order_id AND o.user_id=:user_id
              AND p.provider_reference=:payment_id FOR UPDATE"""),
            {"order_id": order_id, "user_id": user_id, "payment_id": payment_id_bkash}).mappings().first()
        if payment is None:
            return jsonify({"error": "bKash payment not found."}), 404
        if payment["status"] == "paid":
            return jsonify({"status": "COMPLETED", "idempotent": True})
        try:
            result = _request(f"/checkout/payment/execute/{payment_id_bkash}")
        except Exception:
            logger.exception("bKash execute failed order_id=%s payment_id=%s", order_id, payment_id_bkash)
            db.rollback()
            return jsonify({"error": "Could not execute the bKash payment."}), 502

        amount_ok = _money(result.get("amount")) == _money(payment["amount"])
        currency_ok = str(result.get("currency") or payment["currency"] or "BDT").upper() == str(payment["currency"] or "BDT").upper()
        invoice_ok = str(result.get("merchantInvoiceNumber") or payment["transaction_id"]) == str(payment["transaction_id"])
        if not (_success(result) and amount_ok and currency_ok and invoice_ok):
            db.rollback()
            return jsonify({"error": "bKash payment verification failed."}), 400

        trx_id = str(result.get("trxID") or result.get("trxId") or "").strip()
        if not trx_id:
            db.rollback()
            return jsonify({"error": "bKash did not return a transaction ID."}), 502
        db.execute(text("""UPDATE payments SET status='paid',transaction_id=:trx_id,
            provider_reference=:payment_id,updated_at=NOW() WHERE id=:payment_id_db"""),
            {"trx_id": trx_id, "payment_id": payment_id_bkash, "payment_id_db": payment["id"]})
        db.execute(text("""UPDATE commerce_orders SET payment_status='paid',
            status=CASE WHEN status='pending' THEN 'confirmed' ELSE status END,updated_at=NOW()
            WHERE id=:order_id"""), {"order_id": order_id})
        db.commit()
    return jsonify({"status": "COMPLETED", "trxID": trx_id, "order_id": order_id})


@bkash_bp.get("/orders/<int:order_id>/payments/bkash/status")
def query_bkash_payment(order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        payment = db.execute(text("""SELECT p.id,p.status,p.amount,p.currency,p.provider_reference,p.transaction_id
            FROM payments p JOIN commerce_orders o ON o.id=p.order_id
            WHERE p.provider='bkash' AND p.order_id=:order_id AND o.user_id=:user_id
            ORDER BY p.id DESC LIMIT 1 FOR UPDATE"""), {"order_id": order_id, "user_id": user_id}).mappings().first()
        if payment is None:
            return jsonify({"error": "bKash payment not found."}), 404
        if payment["status"] == "paid":
            db.commit()
            return jsonify({"status": "COMPLETED", "idempotent": True})
        if not payment["provider_reference"]:
            db.commit()
            return jsonify({"status": payment["status"]})
        try:
            result = _request(f"/checkout/payment/query/{payment['provider_reference']}", method="GET")
        except Exception:
            logger.exception("bKash query failed order_id=%s", order_id)
            db.rollback()
            return jsonify({"error": "Could not query the bKash payment."}), 502
        amount_ok = _money(result.get("amount")) == _money(payment["amount"])
        currency_ok = str(result.get("currency") or payment["currency"] or "BDT").upper() == str(payment["currency"] or "BDT").upper()
        if _success(result) and amount_ok and currency_ok:
            trx_id = str(result.get("trxID") or result.get("trxId") or "").strip()
            if trx_id:
                db.execute(text("UPDATE payments SET status='paid',transaction_id=:trx_id,updated_at=NOW() WHERE id=:id"),
                           {"trx_id": trx_id, "id": payment["id"]})
                db.execute(text("UPDATE commerce_orders SET payment_status='paid',status=CASE WHEN status='pending' THEN 'confirmed' ELSE status END,updated_at=NOW() WHERE id=:order_id"),
                           {"order_id": order_id})
                db.commit()
                return jsonify({"status": "COMPLETED", "trxID": trx_id})
        db.commit()
        return jsonify({"status": result.get("transactionStatus") or result.get("statusMessage") or payment["status"]})


def register_bkash_routes(app):
    if bkash_bp.name not in app.blueprints:
        app.register_blueprint(bkash_bp)
