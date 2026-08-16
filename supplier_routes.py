"""Dropshipping supplier fulfillment APIs."""
from decimal import Decimal
from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from database import SessionLocal

supplier_bp = Blueprint("supplier_api", __name__, url_prefix="/api")


def _user_id():
    try:
        return int(session.get("user_id")) if session.get("user_id") is not None else None
    except (TypeError, ValueError):
        return None


def _money(v):
    return format(Decimal(str(v or 0)), ".2f")


def register_supplier_routes(app):
    app.register_blueprint(supplier_bp)


@supplier_bp.get("/supplier/products")
def supplier_products():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT sp.id AS supplier_product_id, sp.supplier_id,
                s.company_name, sp.product_id, p.name, p.slug, sp.supplier_sku,
                sp.cost_price, sp.supplier_currency, sp.supplier_stock,
                sp.fulfillment_time_days, sp.is_active
            FROM supplier_products sp
            JOIN supplier_profiles s ON s.id=sp.supplier_id
            JOIN products p ON p.id=sp.product_id
            WHERE s.user_id=:user_id AND sp.is_active=true
            ORDER BY sp.id DESC"""), {"user_id": user_id}).mappings().all()
    return jsonify({"items": [dict(r) | {"cost_price": _money(r["cost_price"])} for r in rows]})


@supplier_bp.get("/supplier/orders")
def supplier_orders():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT so.id, so.order_id, co.order_number,
                so.status, so.external_order_ref, so.tracking_number,
                so.shipping_cost, so.cost_total, so.notes, so.created_at, so.updated_at
            FROM supplier_orders so
            JOIN supplier_profiles s ON s.id=so.supplier_id
            JOIN commerce_orders co ON co.id=so.order_id
            WHERE s.user_id=:user_id
            ORDER BY so.id DESC"""), {"user_id": user_id}).mappings().all()
    return jsonify({"items": [dict(r) | {"shipping_cost": _money(r["shipping_cost"]), "cost_total": _money(r["cost_total"])} for r in rows]})


@supplier_bp.patch("/supplier/orders/<int:supplier_order_id>")
def update_supplier_order(supplier_order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    status = str(body.get("status", "")).strip().lower()
    allowed = {"pending", "submitted", "processing", "shipped", "delivered", "cancelled"}
    if status not in allowed:
        return jsonify({"error": "Invalid supplier order status."}), 400
    external_ref = str(body.get("external_order_ref", "")).strip() or None
    tracking = str(body.get("tracking_number", "")).strip() or None
    if external_ref and len(external_ref) > 180 or tracking and len(tracking) > 180:
        return jsonify({"error": "Reference or tracking number is too long."}), 400
    with SessionLocal() as db:
        row = db.execute(text("""SELECT so.id, so.order_id FROM supplier_orders so
            JOIN supplier_profiles s ON s.id=so.supplier_id
            WHERE so.id=:id AND s.user_id=:user_id FOR UPDATE"""), {"id": supplier_order_id, "user_id": user_id}).mappings().first()
        if row is None:
            return jsonify({"error": "Supplier order not found."}), 404
        db.execute(text("""UPDATE supplier_orders SET status=:status,
            external_order_ref=COALESCE(:external_ref,external_order_ref),
            tracking_number=COALESCE(:tracking,tracking_number), updated_at=NOW()
            WHERE id=:id"""), {"status": status, "external_ref": external_ref, "tracking": tracking, "id": supplier_order_id})
        db.execute(text("""UPDATE commerce_orders SET fulfillment_status=:fulfillment,
            status=CASE WHEN :fulfillment='shipped' AND status NOT IN ('cancelled','refunded') THEN 'shipped'
                        WHEN :fulfillment='delivered' AND status NOT IN ('cancelled','refunded') THEN 'delivered'
                        ELSE status END, updated_at=NOW() WHERE id=:order_id"""), {"fulfillment": status, "order_id": row["order_id"]})
        db.commit()
    return jsonify({"ok": True, "supplier_order_id": supplier_order_id, "status": status})
