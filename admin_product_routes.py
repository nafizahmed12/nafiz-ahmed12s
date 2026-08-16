from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, redirect, request, session, url_for, flash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal

admin_product_bp = Blueprint("admin_product", __name__)


def _admin_required():
    return bool(session.get("admin_logged_in"))


def _money(value):
    return format(Decimal(str(value or 0)), ".2f")


def _product_payload(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "description": row["description"] or "",
        "product_type": row["product_type"],
        "status": row["status"],
        "price": _money(row["price"]),
        "compare_at_price": _money(row["compare_at_price"]) if row["compare_at_price"] is not None else None,
        "currency": row["currency"],
        "sku": row["sku"],
        "stock_quantity": row["stock_quantity"],
        "image_url": row["image_url"],
        "listing_status": row["listing_status"],
        "featured": bool(row["featured"]),
        "created_at": str(row["created_at"]) if row["created_at"] else None,
    }


@admin_product_bp.post("/admin/products")
def create_admin_product():
    if not _admin_required():
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    description = request.form.get("description", "").strip()
    product_type = request.form.get("product_type", "physical").strip().lower()
    status = request.form.get("status", "published").strip().lower()
    currency = request.form.get("currency", "BDT").strip().upper()[:3]
    sku = request.form.get("sku", "").strip() or None
    image_url = request.form.get("image_url", "").strip()
    featured = request.form.get("featured") == "1"

    try:
        price = Decimal(request.form.get("price", "0").strip())
        compare_at_raw = request.form.get("compare_at_price", "").strip()
        compare_at_price = Decimal(compare_at_raw) if compare_at_raw else None
        stock_quantity = int(request.form.get("stock_quantity", "0").strip())
    except (InvalidOperation, ValueError):
        flash("Price, compare-at price and stock must contain valid values.", "error")
        return redirect(url_for("admin"))

    if not name or not slug:
        flash("Product name and slug are required.", "error")
        return redirect(url_for("admin"))
    if not all(c.isalnum() or c == "-" for c in slug) or slug.startswith("-") or slug.endswith("-"):
        flash("Slug may contain only letters, numbers and hyphens.", "error")
        return redirect(url_for("admin"))
    if product_type not in {"physical", "digital"}:
        flash("Product type must be physical or digital.", "error")
        return redirect(url_for("admin"))
    if status not in {"draft", "published"}:
        flash("Product status must be draft or published.", "error")
        return redirect(url_for("admin"))
    if price < 0 or stock_quantity < 0 or (compare_at_price is not None and compare_at_price < 0):
        flash("Price and stock cannot be negative.", "error")
        return redirect(url_for("admin"))
    if product_type == "digital":
        stock_quantity = 0

    with SessionLocal() as db:
        try:
            product_id = db.execute(
                text("""INSERT INTO products
                    (category_id, owner_id, name, slug, description, product_type, status,
                     price, currency, sku, stock_quantity, created_at, updated_at)
                    VALUES (NULL, NULL, :name, :slug, :description, :product_type, :status,
                            :price, :currency, :sku, :stock_quantity, NOW(), NOW())
                    RETURNING id"""),
                {
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "product_type": product_type,
                    "status": status,
                    "price": price,
                    "currency": currency or "BDT",
                    "sku": sku,
                    "stock_quantity": stock_quantity,
                },
            ).scalar_one()

            listing_status = "published" if status == "published" else "draft"
            db.execute(
                text("""INSERT INTO product_listings
                    (product_id, seller_id, supplier_product_id, listing_type, title,
                     price, compare_at_price, currency, stock_quantity, status, featured,
                     created_at, updated_at)
                    VALUES (:product_id, NULL, NULL, 'owned', :title,
                            :price, :compare_at_price, :currency, :stock_quantity,
                            :status, :featured, NOW(), NOW())"""),
                {
                    "product_id": product_id,
                    "title": name,
                    "price": price,
                    "compare_at_price": compare_at_price,
                    "currency": currency or "BDT",
                    "stock_quantity": stock_quantity,
                    "status": listing_status,
                    "featured": featured,
                },
            )

            if image_url:
                db.execute(
                    text("""INSERT INTO product_images
                        (product_id, image_url, alt_text, sort_order, created_at)
                        VALUES (:product_id, :image_url, :alt_text, 0, NOW())"""),
                    {"product_id": product_id, "image_url": image_url, "alt_text": name},
                )
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("A product with this slug or SKU already exists.", "error")
            return redirect(url_for("admin"))

    flash(f"Product '{name}' created successfully.", "success")
    return redirect(url_for("admin"))


@admin_product_bp.get("/api/admin/products")
def admin_products():
    if not _admin_required():
        return jsonify({"error": "Admin authentication required."}), 401

    with SessionLocal() as db:
        rows = db.execute(
            text("""SELECT p.id,p.name,p.slug,p.description,p.product_type,p.status,p.price,
                          p.currency,p.sku,p.stock_quantity,p.created_at,
                          pi.image_url,
                          l.status AS listing_status,l.compare_at_price,l.featured
                   FROM products p
                   LEFT JOIN LATERAL (
                       SELECT image_url FROM product_images
                       WHERE product_id=p.id
                       ORDER BY sort_order ASC,id ASC LIMIT 1
                   ) pi ON TRUE
                   LEFT JOIN LATERAL (
                       SELECT status,compare_at_price,featured
                       FROM product_listings
                       WHERE product_id=p.id
                       ORDER BY id ASC LIMIT 1
                   ) l ON TRUE
                   ORDER BY p.id DESC""")
        ).mappings().all()

    return jsonify({"items": [_product_payload(row) for row in rows]})


@admin_product_bp.post("/api/admin/products/<int:product_id>/archive")
def archive_admin_product(product_id):
    if not _admin_required():
        return jsonify({"error": "Admin authentication required."}), 401

    with SessionLocal() as db:
        result = db.execute(
            text("UPDATE products SET status='archived', updated_at=NOW() WHERE id=:product_id AND status <> 'archived'"),
            {"product_id": product_id},
        )
        db.execute(
            text("UPDATE product_listings SET status='archived', updated_at=NOW() WHERE product_id=:product_id"),
            {"product_id": product_id},
        )
        if result.rowcount == 0:
            db.rollback()
            return jsonify({"error": "Product not found."}), 404
        db.commit()

    return jsonify({"success": True, "product_id": product_id})


def register_admin_product_routes(app):
    if "admin_product" not in app.blueprints:
        app.register_blueprint(admin_product_bp)
