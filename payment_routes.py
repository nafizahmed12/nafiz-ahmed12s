"""Payment abstraction layer for the commerce API.

This layer deliberately keeps gateway-specific credentials and SDKs out of the
core order flow. It supports COD immediately and provides secure, idempotent
payment-intent/webhook primitives for bKash, Nagad, SSLCommerz, and Stripe.
"""

import hashlib
import hmac
import os
from decimal import Decimal

from flask import Blueprint, jsonify, request, session
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
    return format(Decimal(str(value or 0)), ".2f")


def _payment_payload(row):
    return {
        "id": row["id"],
        "order_id": row["order_id"],
        "provider": row["provider"],
        "status": row["status"],
        "amount": _money(row["amount"]),
        "currency": row["currency"],
        "transaction_id": row["transaction_id"],
        "provider_reference": row["provider_reference"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@payment_bp.post("/orders/<int:order_id>/payments")
def create_payment():
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
            FROM commerce_orders WHERE id=:order_id AND user_id=:user_id FOR UPDATE"""), {"order_id": order_id, "user_id": user_id}).mappings().first()
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
            {"order_id": order_id, "provider": provider, "transaction_id": transaction_id, "status": status, "amount": order["total_amount"], "currency": order["currency"]}).scalar_one()
        db.execute(text("UPDATE commerce_orders SET payment_status=:payment_status, updated_at=NOW() WHERE id=:order_id"), {"payment_status": status, "order_id": order_id})
        db.commit()
        payment = db.execute(text("""SELECT id,order_id,provider,status,amount,currency,transaction_id,provider_reference,created_at,updated_at
            FROM payments WHERE id=:payment_id"""), {"payment_id": payment_id}).mappings().one()
    response = {"payment": _payment_payload(payment), "reused": False}
    response["next_step"] = "Gateway initiation must be completed by the configured provider adapter." if provider in ONLINE_PROVIDERS else "Collect payment on delivery; confirm through the protected webhook/admin flow."
    return jsonify(response), 201


@payment_bp.get("/orders/<int:order_id>/payments")
def list_payments(order_id):
    user_id = _user_id()
    if user_id is None: return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        owns = db.execute(text("SELECT 1 FROM commerce_orders WHERE id=:order_id AND user_id=:user_id"), {"order_id": order_id, "user_id": user_id}).scalar_one_or_none()
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
    if status not in {"pending", "initiated", "paid", "failed", "cancelled", "refunded"}: return jsonify({"error": "Invalid payment status."}), 400
    transaction_id = str(body.get("transaction_id", "")).strip() or None
    provider_reference = str(body.get("provider_reference", "")).strip() or None
    with SessionLocal() as db:
        payment = db.execute(text("""SELECT id,order_id,status,amount,currency,transaction_id,provider_reference
            FROM payments WHERE id=:payment_id FOR UPDATE"""), {"payment_id": payment_id}).mappings().first()
        if payment is None: return jsonify({"error": "Payment not found."}), 404
        if payment["status"] == status and (not transaction_id or payment["transaction_id"] == transaction_id):
            db.commit(); return jsonify({"ok": True, "idempotent": True})
        db.execute(text("""UPDATE payments SET status=:status, transaction_id=COALESCE(:transaction_id,transaction_id),
            provider_reference=COALESCE(:provider_reference,provider_reference), updated_at=NOW() WHERE id=:payment_id"""),
            {"status": status, "transaction_id": transaction_id, "provider_reference": provider_reference, "payment_id": payment_id})
        db.execute(text("""UPDATE commerce_orders SET payment_status=:payment_status,
            status=CASE WHEN :payment_status='paid' AND status='pending' THEN 'confirmed'
                        WHEN :payment_status IN ('cancelled','refunded') AND status NOT IN ('shipped','delivered') THEN :payment_status
                        ELSE status END, updated_at=NOW() WHERE id=:order_id"""), {"payment_status": status, "order_id": payment["order_id"]})
        db.commit()
    return jsonify({"ok": True, "payment_id": payment_id, "status": status})


def register_payment_routes(app):
    app.register_blueprint(payment_bp)
    # Register supplier routes here so app.py does not need to be touched again.
    # This keeps the core Flask bootstrap stable during production rollouts.
    try:
        from supplier_routes import register_supplier_routes
        register_supplier_routes(app)
    except ImportError:
        pass
