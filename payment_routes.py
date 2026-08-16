"""Payment abstraction and hosted gateway integration for commerce orders."""

import hashlib
import hmac
import json
import os
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request, session, redirect, render_template
from sqlalchemy import text

from database import SessionLocal

payment_bp = Blueprint("payment_api", __name__, url_prefix="/api")

ONLINE_PROVIDERS = {"bkash", "nagad", "sslcommerz", "stripe"}
ALLOWED_PROVIDERS = ONLINE_PROVIDERS | {"cod", "manual"}


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


def _payment_payload(row):
    return {
        "id": row["id"], "order_id": row["order_id"], "provider": row["provider"],
        "status": row["status"], "amount": _money(row["amount"]), "currency": row["currency"],
        "transaction_id": row["transaction_id"], "provider_reference": row["provider_reference"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@payment_bp.post("/orders/<int:order_id>/payments")
def create_payment(order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    provider = str(body.get("provider", "")).strip().lower()
    transaction_id = str(body.get("transaction_id", "")).strip() or None
    if provider not in ALLOWED_PROVIDERS:
        return jsonify({"error": "Unsupported payment provider."}), 400
    if transaction_id and len(transaction_id) > 160:
        return jsonify({"error": "transaction_id is too long."}), 400
    with SessionLocal() as db:
        order = db.execute(text("""SELECT id, status, payment_status, currency, total_amount
            FROM commerce_orders WHERE id=:order_id AND user_id=:user_id FOR UPDATE"""),
            {"order_id": order_id, "user_id": user_id}).mappings().first()
        if order is None: return jsonify({"error": "Order not found."}), 404
        if order["status"] in {"cancelled", "refunded"}: return jsonify({"error": "This order cannot accept payment."}), 409
        if order["payment_status"] == "paid": return jsonify({"error": "Order is already paid."}), 409
        existing = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE order_id=:order_id AND provider=:provider AND status IN ('pending','initiated')
            ORDER BY id DESC LIMIT 1 FOR UPDATE"""), {"order_id": order_id, "provider": provider}).mappings().first()
        if existing is not None: return jsonify({"payment": _payment_payload(existing), "reused": True})
        status = "pending" if provider in {"cod", "manual"} else "initiated"
        payment_id = db.execute(text("""INSERT INTO payments
            (order_id,provider,transaction_id,status,amount,currency,provider_reference,created_at,updated_at)
            VALUES (:order_id,:provider,:transaction_id,:status,:amount,:currency,NULL,NOW(),NOW()) RETURNING id"""),
            {"order_id": order_id, "provider": provider, "transaction_id": transaction_id,
             "status": status, "amount": order["total_amount"], "currency": order["currency"]}).scalar_one()
        db.execute(text("UPDATE commerce_orders SET payment_status=:payment_status, updated_at=NOW() WHERE id=:order_id"),
                   {"payment_status": status, "order_id": order_id})
        db.commit()
        payment = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE id=:payment_id"""), {"payment_id": payment_id}).mappings().one()
    response = {"payment": _payment_payload(payment), "reused": False}
    response["next_step"] = ("Use /api/orders/<order_id>/payments/sslcommerz/initiate for hosted online checkout."
                              if provider == "sslcommerz" else
                              "Configure the provider adapter before starting this online payment."
                              if provider in ONLINE_PROVIDERS else
                              "Collect payment on delivery/manual channel and confirm through the signed webhook.")
    return jsonify(response), 201


@payment_bp.get("/orders/<int:order_id>/payments")
def list_payments(order_id):
    user_id = _user_id()
    if user_id is None: return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        owns = db.execute(text("SELECT 1 FROM commerce_orders WHERE id=:order_id AND user_id=:user_id"),
                          {"order_id": order_id, "user_id": user_id}).scalar_one_or_none()
        if owns is None: return jsonify({"error": "Order not found."}), 404
        rows = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE order_id=:order_id ORDER BY id DESC"""), {"order_id": order_id}).mappings().all()
    return jsonify({"items": [_payment_payload(row) for row in rows]})


def _valid_webhook_signature(raw_body):
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    signature = request.headers.get("X-Payment-Signature", "").strip()
    if not secret or not signature: return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@payment_bp.post("/payments/webhook")
def payment_webhook():
    raw_body = request.get_data(cache=True)
    if not _valid_webhook_signature(raw_body): return jsonify({"error": "Invalid webhook signature."}), 401
    body = request.get_json(silent=True) or {}
    try: payment_id = int(body.get("payment_id"))
    except (TypeError, ValueError): return jsonify({"error": "payment_id is required."}), 400
    status = str(body.get("status", "")).strip().lower()
    if status not in {"pending", "initiated", "paid", "failed", "cancelled", "refunded"}:
        return jsonify({"error": "Invalid payment status."}), 400
    transaction_id = str(body.get("transaction_id", "")).strip() or None
    provider_reference = str(body.get("provider_reference", "")).strip() or None
    if transaction_id and len(transaction_id) > 160: return jsonify({"error": "transaction_id is too long."}), 400
    if provider_reference and len(provider_reference) > 180: return jsonify({"error": "provider_reference is too long."}), 400
    with SessionLocal() as db:
        payment = db.execute(text("""SELECT id,order_id,status,amount,currency,transaction_id,provider_reference
            FROM payments WHERE id=:payment_id FOR UPDATE"""), {"payment_id": payment_id}).mappings().first()
        if payment is None: return jsonify({"error": "Payment not found."}), 404
        if payment["status"] == status and (not transaction_id or payment["transaction_id"] == transaction_id):
            db.commit(); return jsonify({"ok": True, "idempotent": True})
        _apply_payment_status(db, payment["order_id"], payment_id, status, transaction_id, provider_reference)
        db.commit()
    return jsonify({"ok": True, "payment_id": payment_id, "status": status})


def _apply_payment_status(db, order_id, payment_id, status, transaction_id=None, provider_reference=None):
    db.execute(text("""UPDATE payments SET status=:status, transaction_id=COALESCE(:transaction_id,transaction_id),
        provider_reference=COALESCE(:provider_reference,provider_reference), updated_at=NOW() WHERE id=:payment_id"""),
        {"status": status, "transaction_id": transaction_id, "provider_reference": provider_reference, "payment_id": payment_id})
    db.execute(text("""UPDATE commerce_orders SET payment_status=:payment_status,
        status=CASE WHEN :payment_status='paid' AND status='pending' THEN 'confirmed'
                    WHEN :payment_status IN ('cancelled','refunded') AND status NOT IN ('shipped','delivered') THEN :payment_status
                    WHEN :payment_status='failed' AND status='pending' THEN 'pending'
                    ELSE status END, updated_at=NOW() WHERE id=:order_id"""),
        {"payment_status": status, "order_id": order_id})


def _ssl_base_url():
    return "https://sandbox.sslcommerz.com" if os.getenv("SSLCOMMERZ_SANDBOX", "1") == "1" else "https://securepay.sslcommerz.com"


def _ssl_request(path, data):
    payload = urlencode(data).encode()
    req = Request(f"{_ssl_base_url()}{path}", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _ssl_validate(tran_id):
    store_id = os.getenv("SSLCOMMERZ_STORE_ID", "").strip()
    store_pass = os.getenv("SSLCOMMERZ_STORE_PASSWORD", "").strip()
    if not store_id or not store_pass: return None
    query = urlencode({"tran_id": tran_id, "store_id": store_id, "store_passwd": store_pass, "v": 1, "format": "json"})
    req = Request(f"{_ssl_base_url()}/validator/api/merchantTransIDvalidationAPI.php?{query}", method="GET")
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _callback_url(name):
    base = os.getenv("APP_BASE_URL", "https://nafiz-ahmed12s.onrender.com").rstrip("/")
    return f"{base}/api/payments/sslcommerz/{name}"


@payment_bp.post("/orders/<int:order_id>/payments/sslcommerz/initiate")
def sslcommerz_initiate(order_id):
    user_id = _user_id()
    if user_id is None: return jsonify({"error": "Authentication required."}), 401
    store_id = os.getenv("SSLCOMMERZ_STORE_ID", "").strip()
    store_pass = os.getenv("SSLCOMMERZ_STORE_PASSWORD", "").strip()
    if not store_id or not store_pass:
        return jsonify({"error": "SSLCommerz credentials are not configured on the server."}), 503
    with SessionLocal() as db:
        order = db.execute(text("""SELECT o.id,o.order_number,o.status,o.payment_status,o.currency,o.total_amount,u.username,u.email
            FROM commerce_orders o JOIN users u ON u.id=o.user_id
            WHERE o.id=:order_id AND o.user_id=:user_id FOR UPDATE"""), {"order_id": order_id, "user_id": user_id}).mappings().first()
        if order is None: return jsonify({"error": "Order not found."}), 404
        if order["payment_status"] == "paid": return jsonify({"error": "Order is already paid."}), 409
        payment = db.execute(text("""SELECT id,transaction_id,provider_reference,status,amount,currency FROM payments
            WHERE order_id=:order_id AND provider='sslcommerz' ORDER BY id DESC LIMIT 1 FOR UPDATE"""), {"order_id": order_id}).mappings().first()
        if payment is None:
            payment_id = db.execute(text("""INSERT INTO payments(order_id,provider,transaction_id,status,amount,currency,created_at,updated_at)
                VALUES(:order_id,'sslcommerz',:transaction_id,'initiated',:amount,:currency,NOW(),NOW()) RETURNING id"""),
                {"order_id": order_id, "transaction_id": order["order_number"], "amount": order["total_amount"], "currency": order["currency"]}).scalar_one()
            db.execute(text("UPDATE commerce_orders SET payment_status='initiated',updated_at=NOW() WHERE id=:order_id"), {"order_id": order_id})
            db.commit()
            payment = {"id": payment_id, "transaction_id": order["order_number"], "provider_reference": None, "status": "initiated", "amount": order["total_amount"], "currency": order["currency"]}
        elif payment["status"] == "paid":
            return jsonify({"error": "Order is already paid."}), 409
        tran_id = payment["transaction_id"] or order["order_number"]
        body = {
            "store_id": store_id, "store_passwd": store_pass, "total_amount": _money(order["total_amount"]),
            "currency": order["currency"] or "BDT", "tran_id": tran_id,
            "success_url": _callback_url("success"), "fail_url": _callback_url("fail"), "cancel_url": _callback_url("cancel"),
            "ipn_url": _callback_url("ipn"), "cus_name": order["username"], "cus_email": order["email"],
            "cus_add1": "Bangladesh", "cus_city": "Dhaka", "cus_state": "Dhaka", "cus_postcode": "1000", "cus_country": "Bangladesh",
            "shipping_method": "NO", "product_name": "Nafiz Commerce Order", "product_category": "General", "product_profile": "general",
        }
        try: result = _ssl_request("/gwprocess/v4/api.php", body)
        except Exception:
            db.rollback(); return jsonify({"error": "Could not connect to SSLCommerz."}), 502
        if result.get("status") != "SUCCESS" or not result.get("GatewayPageURL"):
            db.rollback(); return jsonify({"error": "SSLCommerz rejected the payment request.", "provider_response": result}), 502
        db.execute(text("UPDATE payments SET provider_reference=:reference,transaction_id=:tran_id,status='initiated',updated_at=NOW() WHERE id=:payment_id"),
                   {"reference": result.get("sessionkey"), "tran_id": tran_id, "payment_id": payment["id"]})
        db.commit()
    return jsonify({"payment_id": payment["id"], "status": "initiated", "gateway_page_url": result["GatewayPageURL"], "session_key": result.get("sessionkey")})


def _ssl_callback(status):
    body = request.form.to_dict() or (request.get_json(silent=True) or {})
    tran_id = str(body.get("tran_id", "")).strip()
    if not tran_id: return jsonify({"error": "tran_id is required."}), 400
    with SessionLocal() as db:
        payment = db.execute(text("SELECT id,order_id,amount,currency,status FROM payments WHERE provider='sslcommerz' AND transaction_id=:tran_id FOR UPDATE"), {"tran_id": tran_id}).mappings().first()
        if payment is None: return jsonify({"error": "Payment not found."}), 404
        if status == "success":
            try: validation = _ssl_validate(tran_id)
            except Exception: return jsonify({"error": "Could not validate SSLCommerz transaction."}), 502
            valid = validation and validation.get("status") in {"VALID", "VALIDATED"}
            amount_ok = valid and _money(validation.get("amount")) == _money(payment["amount"])
            currency_ok = valid and str(validation.get("currency", "")).upper() == str(payment["currency"] or "BDT").upper()
            if not (valid and amount_ok and currency_ok): return jsonify({"error": "Payment validation failed."}), 400
            _apply_payment_status(db, payment["order_id"], payment["id"], "paid", validation.get("bank_tran_id"), validation.get("val_id"))
            db.commit()
            return redirect(f"{os.getenv('APP_BASE_URL','https://nafiz-ahmed12s.onrender.com').rstrip('/')}/payment/success?order_id={payment['order_id']}")
        target = "failed" if status == "fail" else "cancelled"
        _apply_payment_status(db, payment["order_id"], payment["id"], target, body.get("bank_tran_id"), body.get("sessionkey"))
        db.commit()
    return redirect(f"{os.getenv('APP_BASE_URL','https://nafiz-ahmed12s.onrender.com').rstrip('/')}/payment/{status}?order_id={payment['order_id']}")


@payment_bp.post("/payments/sslcommerz/success")
def sslcommerz_success(): return _ssl_callback("success")

@payment_bp.post("/payments/sslcommerz/fail")
def sslcommerz_fail(): return _ssl_callback("fail")

@payment_bp.post("/payments/sslcommerz/cancel")
def sslcommerz_cancel(): return _ssl_callback("cancel")

@payment_bp.post("/payments/sslcommerz/ipn")
def sslcommerz_ipn(): return _ssl_callback("success")


@payment_bp.get("/../payment/<string:result>")
def invalid_result_route(result):
    return redirect(f"/payment/{result}")


@payment_bp.get("/payment-result/<string:result>")
def payment_result(result):
    if result not in {"success", "fail", "cancel"}: return jsonify({"error": "Invalid payment result."}), 404
    return render_template("payment_result.html", result=result)


def register_payment_routes(app):
    if payment_bp.name not in app.blueprints:
        app.register_blueprint(payment_bp)
