from decimal import Decimal, InvalidOperation
import base64

from flask import Blueprint, jsonify, redirect, request, url_for, flash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from admin_auth import admin_required

admin_product_bp = Blueprint("admin_product", __name__)


def _money(value):
    return format(Decimal(str(value or 0)), ".2f")


def _product_payload(row):
    return {
        "id": row["id"], "name": row["name"], "slug": row["slug"],
        "description": row["description"] or "", "product_type": row["product_type"],
        "status": row["status"], "price": _money(row["price"]),
        "compare_at_price": _money(row["compare_at_price"]) if row["compare_at_price"] is not None else None,
        "currency": row["currency"], "sku": row["sku"], "stock_quantity": row["stock_quantity"],
        "image_url": row["image_url"], "listing_status": row["listing_status"],
        "featured": bool(row["featured"]), "category": row["category_slug"] or "",
        "created_at": str(row["created_at"]) if row["created_at"] else None,
    }


def _uploaded_image_data_url():
    file = request.files.get("image")
    if not file or not file.filename:
        return ""
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
    content_type = (file.mimetype or "").lower()
    if content_type not in allowed:
        raise ValueError("Image must be JPG, PNG, WEBP or GIF.")
    raw = file.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Image must be 1 MB or smaller.")
    if not raw:
        raise ValueError("The selected image is empty.")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _parse_product_form():
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip().lower()
    product_type = request.form.get("product_type", "physical").strip().lower()
    status = request.form.get("status", "published").strip().lower()
    currency = request.form.get("currency", "BDT").strip().upper()[:3] or "BDT"
    sku = request.form.get("sku", "").strip() or None
    image_url = request.form.get("image_url", "").strip()
    uploaded_image = _uploaded_image_data_url()
    if uploaded_image:
        image_url = uploaded_image
    featured = request.form.get("featured") == "1"
    try:
        price = Decimal(request.form.get("price", "0").strip())
        compare_raw = request.form.get("compare_at_price", "").strip()
        compare_at_price = Decimal(compare_raw) if compare_raw else None
        stock_quantity = int(request.form.get("stock_quantity", "0").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Price, original price and stock must contain valid values.")
    if not name or not slug or not category:
        raise ValueError("Product name, slug and category are required.")
    if not all(c.isalnum() or c == "-" for c in slug) or slug.startswith("-") or slug.endswith("-"):
        raise ValueError("Slug may contain only letters, numbers and hyphens.")
    if product_type not in {"physical", "digital"}:
        raise ValueError("Product type must be physical or digital.")
    if status not in {"draft", "published"}:
        raise ValueError("Product status must be draft or published.")
    if price < 0 or stock_quantity < 0 or (compare_at_price is not None and compare_at_price < 0):
        raise ValueError("Price and stock cannot be negative.")
    if compare_at_price is not None and compare_at_price <= price:
        raise ValueError("Original price must be higher than the sale price.")
    if product_type == "digital":
        stock_quantity = 0
    return locals()


def _category_id(db, slug):
    return db.execute(text("SELECT id FROM product_categories WHERE LOWER(slug)=:slug LIMIT 1"), {"slug": slug}).scalar_one_or_none()


@admin_product_bp.post("/admin/products")
@admin_required
def create_admin_product():
    try:
        data = _parse_product_form()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin"))
    with SessionLocal() as db:
        category_id = _category_id(db, data["category"])
        if category_id is None:
            flash("Selected category does not exist.", "error")
            return redirect(url_for("admin"))
        try:
            product_id = db.execute(text("""INSERT INTO products
                (category_id,owner_id,name,slug,description,product_type,status,price,currency,sku,stock_quantity,created_at,updated_at)
                VALUES (:category_id,NULL,:name,:slug,:description,:product_type,:status,:price,:currency,:sku,:stock_quantity,NOW(),NOW())
                RETURNING id"""), {**data, "category_id": category_id}).scalar_one()
            listing_status = "published" if data["status"] == "published" else "draft"
            db.execute(text("""INSERT INTO product_listings
                (product_id,seller_id,supplier_product_id,listing_type,title,price,compare_at_price,currency,stock_quantity,status,featured,created_at,updated_at)
                VALUES (:product_id,NULL,NULL,'owned',:name,:price,:compare_at_price,:currency,:stock_quantity,:listing_status,:featured,NOW(),NOW())"""),
                {**data, "product_id": product_id, "listing_status": listing_status})
            if data["image_url"]:
                db.execute(text("""INSERT INTO product_images(product_id,image_url,alt_text,sort_order,created_at)
                    VALUES(:product_id,:image_url,:name,0,NOW())"""), {"product_id": product_id, "image_url": data["image_url"], "name": data["name"]})
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("A product with this slug or SKU already exists.", "error")
            return redirect(url_for("admin"))
    flash(f"Product '{data['name']}' created successfully.", "success")
    return redirect(url_for("admin"))


@admin_product_bp.post("/api/admin/products/<int:product_id>/edit")
@admin_required
def edit_admin_product(product_id):
    try:
        data = _parse_product_form()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with SessionLocal() as db:
        category_id = _category_id(db, data["category"])
        if category_id is None:
            return jsonify({"error": "Selected category does not exist."}), 400
        try:
            exists = db.execute(text("SELECT id FROM products WHERE id=:id"), {"id": product_id}).scalar_one_or_none()
            if exists is None:
                return jsonify({"error": "Product not found."}), 404
            db.execute(text("""UPDATE products SET category_id=:category_id,name=:name,slug=:slug,description=:description,
                product_type=:product_type,status=:status,price=:price,currency=:currency,sku=:sku,stock_quantity=:stock_quantity,updated_at=NOW()
                WHERE id=:id"""), {**data, "category_id": category_id, "id": product_id})
            listing_status = "published" if data["status"] == "published" else "draft"
            listing_id = db.execute(text("SELECT id FROM product_listings WHERE product_id=:id ORDER BY id LIMIT 1"), {"id": product_id}).scalar_one_or_none()
            listing_data = {**data, "id": product_id, "listing_status": listing_status}
            if listing_id is None:
                db.execute(text("""INSERT INTO product_listings(product_id,seller_id,supplier_product_id,listing_type,title,price,compare_at_price,currency,stock_quantity,status,featured,created_at,updated_at)
                    VALUES(:id,NULL,NULL,'owned',:name,:price,:compare_at_price,:currency,:stock_quantity,:listing_status,:featured,NOW(),NOW())"""), listing_data)
            else:
                db.execute(text("""UPDATE product_listings SET title=:name,price=:price,compare_at_price=:compare_at_price,currency=:currency,
                    stock_quantity=:stock_quantity,status=:listing_status,featured=:featured,updated_at=NOW() WHERE id=:listing_id"""), {**listing_data, "listing_id": listing_id})
            if data["image_url"]:
                image_id = db.execute(text("SELECT id FROM product_images WHERE product_id=:id ORDER BY sort_order,id LIMIT 1"), {"id": product_id}).scalar_one_or_none()
                if image_id:
                    db.execute(text("UPDATE product_images SET image_url=:image_url,alt_text=:name WHERE id=:image_id"), {**data, "image_id": image_id})
                else:
                    db.execute(text("INSERT INTO product_images(product_id,image_url,alt_text,sort_order,created_at) VALUES(:id,:image_url,:name,0,NOW())"), {**data, "id": product_id})
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"error": "A product with this slug or SKU already exists."}), 409
    return jsonify({"success": True, "product_id": product_id})


@admin_product_bp.get("/api/admin/products")
@admin_required
def admin_products():
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT p.id,p.name,p.slug,p.description,p.product_type,p.status,p.price,p.currency,p.sku,p.stock_quantity,p.created_at,
            pi.image_url,pc.slug AS category_slug,l.status AS listing_status,l.compare_at_price,l.featured
            FROM products p
            LEFT JOIN product_categories pc ON pc.id=p.category_id
            LEFT JOIN LATERAL(SELECT image_url FROM product_images WHERE product_id=p.id ORDER BY sort_order,id LIMIT 1) pi ON TRUE
            LEFT JOIN LATERAL(SELECT status,compare_at_price,featured FROM product_listings WHERE product_id=p.id ORDER BY id LIMIT 1) l ON TRUE
            ORDER BY p.id DESC""")).mappings().all()
    return jsonify({"items": [_product_payload(row) for row in rows]})


@admin_product_bp.post("/api/admin/products/<int:product_id>/archive")
@admin_required
def archive_admin_product(product_id):
    with SessionLocal() as db:
        result = db.execute(text("UPDATE products SET status='archived',updated_at=NOW() WHERE id=:id AND status<>'archived'"), {"id": product_id})
        db.execute(text("UPDATE product_listings SET status='archived',updated_at=NOW() WHERE product_id=:id"), {"id": product_id})
        if result.rowcount == 0:
            db.rollback()
            return jsonify({"error": "Product not found."}), 404
        db.commit()
    return jsonify({"success": True, "product_id": product_id})


def register_admin_product_routes(app):
    if "admin_product" not in app.blueprints:
        app.register_blueprint(admin_product_bp)
