from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from sqlalchemy import text

from database import SessionLocal
from admin_auth import admin_required

admin_affiliate_bp = Blueprint("admin_affiliate", __name__)


def _valid_http_url(value, max_len):
    value = (value or "").strip()
    if not value or len(value) > max_len:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return value


def _parse_affiliate_form(body):
    name = str(body.get("name") or "").strip()[:255]
    if not name:
        raise ValueError("Name is required.")
    amazon_url = _valid_http_url(body.get("amazon_url"), 2048)
    if amazon_url is None:
        raise ValueError("Enter a valid http(s) Amazon product link.")
    image_url = body.get("image_url")
    if image_url:
        image_url = _valid_http_url(image_url, 2048)
        if image_url is None:
            raise ValueError("Image link must be a valid http(s) URL.")
    description = str(body.get("description") or "").strip()[:2000] or None
    display_price = str(body.get("display_price") or "").strip()[:50] or None
    status = str(body.get("status") or "published").strip().lower()
    if status not in ("published", "draft"):
        raise ValueError("Status must be published or draft.")
    try:
        sort_order = int(body.get("sort_order") or 0)
    except (TypeError, ValueError):
        raise ValueError("Sort order must be a whole number.")
    return {
        "name": name, "amazon_url": amazon_url, "image_url": image_url,
        "description": description, "display_price": display_price,
        "status": status, "sort_order": sort_order,
    }


def _affiliate_payload(row):
    return {
        "id": row["id"], "name": row["name"], "description": row["description"] or "",
        "amazon_url": row["amazon_url"], "image_url": row["image_url"],
        "display_price": row["display_price"] or "", "status": row["status"],
        "sort_order": row["sort_order"],
        "created_at": str(row["created_at"]) if row["created_at"] else None,
    }


@admin_affiliate_bp.get("/api/admin/affiliate-products")
@admin_required
def admin_list_affiliate_products():
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT id,name,description,amazon_url,image_url,display_price,status,sort_order,created_at
            FROM affiliate_products ORDER BY sort_order ASC,id DESC""")).mappings().all()
    return jsonify({"items": [_affiliate_payload(r) for r in rows]})


@admin_affiliate_bp.post("/api/admin/affiliate-products")
@admin_required
def create_affiliate_product():
    try:
        data = _parse_affiliate_form(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with SessionLocal() as db:
        new_id = db.execute(text("""INSERT INTO affiliate_products
            (name,description,amazon_url,image_url,display_price,sort_order,status,created_at,updated_at)
            VALUES (:name,:description,:amazon_url,:image_url,:display_price,:sort_order,:status,NOW(),NOW())
            RETURNING id"""), data).scalar_one()
        db.commit()
    return jsonify({"success": True, "id": new_id}), 201


@admin_affiliate_bp.patch("/api/admin/affiliate-products/<int:item_id>")
@admin_required
def update_affiliate_product(item_id):
    try:
        data = _parse_affiliate_form(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with SessionLocal() as db:
        exists = db.execute(text("SELECT id FROM affiliate_products WHERE id=:id"), {"id": item_id}).scalar_one_or_none()
        if exists is None:
            return jsonify({"error": "Affiliate product not found."}), 404
        db.execute(text("""UPDATE affiliate_products SET name=:name,description=:description,amazon_url=:amazon_url,
            image_url=:image_url,display_price=:display_price,sort_order=:sort_order,status=:status,updated_at=NOW()
            WHERE id=:id"""), {**data, "id": item_id})
        db.commit()
    return jsonify({"success": True, "id": item_id})


@admin_affiliate_bp.delete("/api/admin/affiliate-products/<int:item_id>")
@admin_required
def delete_affiliate_product(item_id):
    with SessionLocal() as db:
        result = db.execute(text("DELETE FROM affiliate_products WHERE id=:id"), {"id": item_id})
        if result.rowcount == 0:
            db.rollback()
            return jsonify({"error": "Affiliate product not found."}), 404
        db.commit()
    return jsonify({"success": True, "id": item_id})


def register_admin_affiliate_routes(app):
    if "admin_affiliate" not in app.blueprints:
        app.register_blueprint(admin_affiliate_bp)
