import hashlib
import hmac
import json
import logging
import os
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request, session, redirect, render_template
from sqlalchemy import text

from database import SessionLocal
from schema import allow_payment_attempt

payment_bp = Blueprint("payment_api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

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
    if not allow_payment_attempt(request.remote_addr, user_id):
        return jsonify({"error": "Too many payment attempts. Please wait a few minutes and try again."}), 429
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
        if order is None:
            return jsonify({"error": "Order not found."}), 404
        if order["status"] in {"cancelled", "refunded"}:
            return jsonify({"error": "This order cannot accept payment."}), 409
        if order["payment_status"] == "paid":
            return jsonify({"error": "Order is already paid."}), 409
        existing = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE order_id=:order_id AND provider=:provider AND status IN ('pending','initiated')
            ORDER BY id DESC LIMIT 1 FOR UPDATE"""),
            {"order_id": order_id, "provider": provider}).mappings().first()
        if existing is not None:
            return jsonify({"payment": _payment_payload(existing), "reused": True})
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
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        owns = db.execute(text("SELECT 1 FROM commerce_orders WHERE id=:order_id AND user_id=:user_id"),
                          {"order_id": order_id, "user_id": user_id}).scalar_one_or_none()
        if owns is None:
            return jsonify({"error": "Order not found."}), 404
        rows = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE order_id=:order_id ORDER BY id DESC"""), {"order_id": order_id}).mappings().all()
    return jsonify({"items": [_payment_payload(row) for row in rows]})


def _valid_webhook_signature(raw_body):
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    signature = request.headers.get("X-Payment-Signature", "").strip()
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@payment_bp.post("/payments/webhook")
def payment_webhook():
    raw_body = request.get_data(cache=True)
    if not _valid_webhook_signature(raw_body):
        return jsonify({"error": "Invalid webhook signature."}), 401
    body = request.get_json(silent=True) or {}
    try:
        payment_id = int(body.get("payment_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "payment_id is required."}), 400
    status = str(body.get("status", "")).strip().lower()
    if status not in {"pending", "initiated", "paid", "failed", "cancelled", "refunded"}:
        return jsonify({"error": "Invalid payment status."}), 400
    transaction_id = str(body.get("transaction_id", "")).strip() or None
    provider_reference = str(body.get("provider_reference", "")).strip() or None
    if transaction_id and len(transaction_id) > 160:
        return jsonify({"error": "transaction_id is too long."}), 400
    if provider_reference and len(provider_reference) > 180:
        return jsonify({"error": "provider_reference is too long."}), 400
    with SessionLocal() as db:
        payment = db.execute(text("""SELECT id,order_id,status,amount,currency,transaction_id,provider_reference
            FROM payments WHERE id=:payment_id FOR UPDATE"""), {"payment_id": payment_id}).mappings().first()
        if payment is None:
            return jsonify({"error": "Payment not found."}), 404
        if payment["status"] == status and (not transaction_id or payment["transaction_id"] == transaction_id):
            db.commit()
            return jsonify({"ok": True, "idempotent": True})
        _apply_payment_status(db, payment["order_id"], payment_id, status, transaction_id, provider_reference,
                              current_status=payment["status"])
        db.commit()
    return jsonify({"ok": True, "payment_id": payment_id, "status": status})


def _apply_payment_status(db, order_id, payment_id, status, transaction_id=None, provider_reference=None,
                          current_status=None):
    """Apply a payment transition without allowing stale webhooks to downgrade terminal states.

    ``paid`` may transition only to ``refunded``. ``refunded`` and ``cancelled``
    are terminal. Unknown/current states are still handled conservatively by
    rejecting backwards transitions instead of trusting webhook ordering.
    """
    if current_status is None:
        current_status = db.execute(
            text("SELECT status FROM payments WHERE id=:payment_id FOR UPDATE"),
            {"payment_id": payment_id},
        ).scalar_one_or_none()

    terminal_transitions = {
        "paid": {"paid", "refunded"},
        "refunded": {"refunded"},
        "cancelled": {"cancelled"},
    }
    if current_status in terminal_transitions and status not in terminal_transitions[current_status]:
        logger.warning("Ignoring stale payment transition payment_id=%s current=%s requested=%s",
                       payment_id, current_status, status)
        return False

    db.execute(text("""UPDATE payments SET status=:status, transaction_id=COALESCE(:transaction_id,transaction_id),
        provider_reference=COALESCE(:provider_reference,provider_reference), updated_at=NOW() WHERE id=:payment_id"""),
        {"status": status, "transaction_id": transaction_id, "provider_reference": provider_reference, "payment_id": payment_id})
    db.execute(text("""UPDATE commerce_orders SET payment_status=:payment_status,
        status=CASE WHEN :payment_status='paid' AND status='pending' THEN 'confirmed'
                    WHEN :payment_status IN ('cancelled','refunded') AND status NOT IN ('shipped','delivered') THEN :payment_status
                    WHEN :payment_status='failed' AND status='pending' THEN 'pending'
                    ELSE status END, updated_at=NOW() WHERE id=:order_id"""),
        {"payment_status": status, "order_id": order_id})
    return True


def _ssl_base_url():
    return "https://sandbox.sslcommerz.com" if os.getenv("SSLCOMMERZ_SANDBOX", "1") == "1" else "https://securepay.sslcommerz.com"


def _ssl_request(path, data):
    payload = urlencode(data).encode()
    base_url = _ssl_base_url()
    req = Request(f"{base_url}{path}", data=payload,
                  headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    logger.info("SSLCommerz request start endpoint=%s sandbox=%s", path, "1" if "sandbox.sslcommerz.com" in base_url else "0")
    with urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="replace")
        logger.info("SSLCommerz response status=%s content_type=%s body_length=%s", response.status,
                    response.headers.get("Content-Type"), len(raw))
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("SSLCommerz returned non-JSON response body_preview=%r", raw[:500])
            raise


def _ssl_validate(val_id=None, tran_id=None):
    """Validate a successful SSLCommerz transaction server-side.

    Prefer the official Order Validation API with val_id from the callback.
    If val_id is absent, fall back to the Merchant Transaction ID API and
    extract the matching transaction from its element[] response.
    """
    store_id = os.getenv("SSLCOMMERZ_STORE_ID", "").strip()
    store_pass = os.getenv("SSLCOMMERZ_STORE_PASSWORD", "").strip()
    if not store_id or not store_pass:
        return None

    base_url = _ssl_base_url()
    if val_id:
        query = urlencode({"val_id": val_id, "store_id": store_id, "store_passwd": store_pass, "v": 1, "format": "json"})
        endpoint = f"{base_url}/validator/api/validationserverAPI.php?{query}"
    elif tran_id:
        query = urlencode({"tran_id": tran_id, "store_id": store_id, "store_passwd": store_pass, "v": 1, "format": "json"})
        endpoint = f"{base_url}/validator/api/merchantTransIDvalidationAPI.php?{query}"
    else:
        return None

    req = Request(endpoint, method="GET")
    with urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("SSLCommerz validation returned non-JSON response status=%s body_preview=%r", response.status, raw[:500])
            raise

    if val_id:
        logger.info("SSLCommerz validation result tran_id=%s val_id=%s status=%r amount=%r currency=%r APIConnect=%r",
                    result.get("tran_id"), result.get("val_id"), result.get("status"),
                    result.get("amount"), result.get("currency"), result.get("APIConnect"))
        return result

    elements = result.get("element") or []
    if isinstance(elements, list):
        for element in elements:
            if str(element.get("tran_id", "")) == str(tran_id):
                logger.info("SSLCommerz merchant validation matched tran_id=%s status=%r amount=%r currency=%r",
                            tran_id, element.get("status"), element.get("amount"), element.get("currency"))
                return element
    logger.warning("SSLCommerz merchant validation returned no matching transaction tran_id=%s response_keys=%s",
                   tran_id, list(result.keys()) if isinstance(result, dict) else type(result).__name__)
    return None


def _callback_url(name):
    base = os.getenv("APP_BASE_URL", "https://nafiz-ahmed12s.onrender.com").rstrip("/")
    return f"{base}/api/payments/sslcommerz/{name}"
