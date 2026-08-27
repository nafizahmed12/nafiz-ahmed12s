from decimal import Decimal

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import text

from database import SessionLocal
from admin_auth import admin_required

admin_orders_bp = Blueprint("admin_orders", __name__)

# Keep these values aligned with the order states already stored in the database.
ORDER_STATUSES = {"pending", "processing", "confirmed", "completed", "cancelled", "refunded"}
FULFILLMENT_STATUSES = {"unfulfilled", "processing", "fulfilled", "shipped", "delivered", "cancelled"}
PAYMENT_STATUSES = {"pending", "initiated", "paid", "failed", "refunded", "cancelled"}


def _money(value):
    return format(Decimal(str(value or 0)), ".2f")


@admin_orders_bp.get("/admin/orders")
@admin_required
def admin_orders():
    return render_template("admin_orders.html")


@admin_orders_bp.get("/api/admin/orders")
@admin_required
def admin_orders_api():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT o.id,o.order_number,o.user_id,o.status,o.payment_status,o.fulfillment_status,
                   o.currency,o.subtotal,o.shipping_amount,o.discount_amount,o.total_amount,o.created_at,
                   u.username,u.email,
                   COALESCE((SELECT COUNT(*) FROM commerce_order_items oi WHERE oi.order_id=o.id),0) AS item_count
            FROM commerce_orders o
            JOIN users u ON u.id=o.user_id
            ORDER BY o.id DESC
            LIMIT 200
        """)).mappings().all()
    return jsonify({"items": [
        {
            "id": r["id"], "order_number": r["order_number"], "user_id": r["user_id"],
            "username": r["username"], "email": r["email"], "status": r["status"],
            "payment_status": r["payment_status"], "fulfillment_status": r["fulfillment_status"],
            "currency": r["currency"], "subtotal": _money(r["subtotal"]),
            "shipping_amount": _money(r["shipping_amount"]), "discount_amount": _money(r["discount_amount"]),
            "total_amount": _money(r["total_amount"]), "item_count": r["item_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        } for r in rows
    ]})


@admin_orders_bp.get("/api/admin/orders/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    with SessionLocal() as db:
        order = db.execute(text("""
            SELECT o.id,o.order_number,o.user_id,o.status,o.payment_status,o.fulfillment_status,
                   o.currency,o.subtotal,o.shipping_amount,o.discount_amount,o.total_amount,o.created_at,
                   u.username,u.email
            FROM commerce_orders o JOIN users u ON u.id=o.user_id
            WHERE o.id=:id
        """), {"id": order_id}).mappings().first()
        if order is None:
            return jsonify({"error": "Order not found."}), 404
        items = db.execute(text("""
            SELECT product_name,quantity,unit_price,line_total
            FROM commerce_order_items WHERE order_id=:id ORDER BY id
        """), {"id": order_id}).mappings().all()
        payments = db.execute(text("""
            SELECT provider,transaction_id,status,amount,currency,provider_reference,created_at
            FROM payments WHERE order_id=:id ORDER BY id DESC
        """), {"id": order_id}).mappings().all()
    return jsonify({
        "id": order["id"], "order_number": order["order_number"], "user_id": order["user_id"],
        "username": order["username"], "email": order["email"], "status": order["status"],
        "payment_status": order["payment_status"], "fulfillment_status": order["fulfillment_status"],
        "currency": order["currency"], "subtotal": _money(order["subtotal"]),
        "shipping_amount": _money(order["shipping_amount"]), "discount_amount": _money(order["discount_amount"]),
        "total_amount": _money(order["total_amount"]),
        "created_at": order["created_at"].isoformat() if order["created_at"] else None,
        "items": [{"product_name": x["product_name"], "quantity": x["quantity"], "unit_price": _money(x["unit_price"]), "line_total": _money(x["line_total"])} for x in items],
        "payments": [{"provider": x["provider"], "transaction_id": x["transaction_id"], "status": x["status"], "amount": _money(x["amount"]), "currency": x["currency"], "provider_reference": x["provider_reference"], "created_at": x["created_at"].isoformat() if x["created_at"] else None} for x in payments],
    })


@admin_orders_bp.patch("/api/admin/orders/<int:order_id>")
@admin_required
def update_admin_order(order_id):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    payment_status = body.get("payment_status")
    fulfillment_status = body.get("fulfillment_status")
    if status is not None and status not in ORDER_STATUSES:
        return jsonify({"error": "Invalid order status."}), 400
    if payment_status is not None and payment_status not in PAYMENT_STATUSES:
        return jsonify({"error": "Invalid payment status."}), 400
    if fulfillment_status is not None and fulfillment_status not in FULFILLMENT_STATUSES:
        return jsonify({"error": "Invalid fulfillment status."}), 400
    if status is None and payment_status is None and fulfillment_status is None:
        return jsonify({"error": "No status changes supplied."}), 400
    with SessionLocal() as db:
        exists = db.execute(text("SELECT id FROM commerce_orders WHERE id=:id"), {"id": order_id}).scalar_one_or_none()
        if exists is None:
            return jsonify({"error": "Order not found."}), 404
        db.execute(text("""
            UPDATE commerce_orders SET
              status=COALESCE(:status,status),
              payment_status=COALESCE(:payment_status,payment_status),
              fulfillment_status=COALESCE(:fulfillment_status,fulfillment_status),
              updated_at=NOW()
            WHERE id=:id
        """), {"id": order_id, "status": status, "payment_status": payment_status, "fulfillment_status": fulfillment_status})
        db.commit()
    return jsonify({"success": True, "order_id": order_id})


def register_admin_orders_routes(app):
    if "admin_orders" not in app.blueprints:
        app.register_blueprint(admin_orders_bp)
