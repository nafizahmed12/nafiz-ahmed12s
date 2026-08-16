from decimal import Decimal
from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal

seller_bp = Blueprint("seller_api", __name__, url_prefix="/api/seller")


def _user_id():
    value = session.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _seller(db, user_id, for_update=False):
    lock = " FOR UPDATE" if for_update else ""
    return db.execute(
        text(f"SELECT id,user_id,store_name,store_slug,description,status,commission_rate,created_at,updated_at FROM seller_profiles WHERE user_id=:user_id{lock}"),
        {"user_id": user_id},
    ).mappings().first()


def _money(value):
    return format(Decimal(str(value or 0)), ".2f")


@seller_bp.post("/register")
def register_seller():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    store_name = str(body.get("store_name", "")).strip()
    store_slug = str(body.get("store_slug", "")).strip().lower()
    description = str(body.get("description", "")).strip()
    if not store_name or not store_slug:
        return jsonify({"error": "store_name and store_slug are required."}), 400
    if len(store_name) > 160 or len(store_slug) > 180:
        return jsonify({"error": "Store name or slug is too long."}), 400
    if not all(c.isalnum() or c in "-_" for c in store_slug):
        return jsonify({"error": "store_slug may contain only letters, numbers, hyphens and underscores."}), 400
    with SessionLocal() as db:
        existing = _seller(db, user_id, for_update=True)
        if existing:
            return jsonify({"error": "Seller profile already exists.", "seller": dict(existing)}), 409
        slug_exists = db.execute(text("SELECT 1 FROM seller_profiles WHERE store_slug=:slug"), {"slug": store_slug}).first()
        if slug_exists:
            return jsonify({"error": "Store slug already exists."}), 409
        seller_id = db.execute(text("INSERT INTO seller_profiles (user_id,store_name,store_slug,description,status,commission_rate,created_at,updated_at) VALUES (:user_id,:store_name,:slug,:description,'pending',10,NOW(),NOW()) RETURNING id"), {"user_id": user_id, "store_name": store_name, "slug": store_slug, "description": description}).scalar_one()
        db.commit()
    return jsonify({"seller_id": seller_id, "status": "pending"}), 201


@seller_bp.get("/profile")
def seller_profile():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        seller = _seller(db, user_id)
    if not seller:
        return jsonify({"error": "Seller profile not found."}), 404
    return jsonify(dict(seller))


@seller_bp.get("/products")
def seller_products():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        seller = _seller(db, user_id)
        if not seller:
            return jsonify({"error": "Seller profile not found."}), 404
        rows = db.execute(text("""SELECT ps.id,ps.product_id,ps.seller_price,ps.seller_stock,ps.is_active,p.name,p.slug,p.product_type,p.status
            FROM product_sellers ps JOIN products p ON p.id=ps.product_id
            WHERE ps.seller_id=:seller_id ORDER BY ps.id DESC"""), {"seller_id": seller["id"]}).mappings().all()
    return jsonify({"items": [{**dict(row), "seller_price": _money(row["seller_price"])} for row in rows]})


@seller_bp.post("/products")
def create_seller_product():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    try:
        product_id = int(body.get("product_id"))
        seller_price = Decimal(str(body.get("seller_price")))
        seller_stock = int(body.get("seller_stock", 0))
    except (TypeError, ValueError, ArithmeticError):
        return jsonify({"error": "product_id, seller_price and seller_stock are invalid."}), 400
    if seller_price < 0 or seller_stock < 0:
        return jsonify({"error": "Price and stock cannot be negative."}), 400
    with SessionLocal() as db:
        seller = _seller(db, user_id, for_update=True)
        if not seller:
            return jsonify({"error": "Seller profile not found."}), 404
        if seller["status"] != "approved":
            return jsonify({"error": "Seller account must be approved before listing products."}), 403
        product = db.execute(text("SELECT id FROM products WHERE id=:product_id AND status NOT IN ('archived')"), {"product_id": product_id}).first()
        if not product:
            return jsonify({"error": "Product not found."}), 404
        try:
            row = db.execute(text("""INSERT INTO product_sellers (seller_id,product_id,seller_price,seller_stock,is_active,created_at,updated_at)
                VALUES (:seller_id,:product_id,:price,:stock,TRUE,NOW(),NOW())
                RETURNING id,product_id,seller_price,seller_stock,is_active"""), {"seller_id": seller["id"], "product_id": product_id, "price": seller_price, "stock": seller_stock}).mappings().one()
        except IntegrityError:
            db.rollback()
            return jsonify({"error": "This product is already listed by your store."}), 409
        db.commit()
    return jsonify({**dict(row), "seller_price": _money(row["seller_price"])}), 201


@seller_bp.patch("/products/<int:listing_id>")
def update_seller_product(listing_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    with SessionLocal() as db:
        seller = _seller(db, user_id, for_update=True)
        if not seller:
            return jsonify({"error": "Seller profile not found."}), 404
        row = db.execute(text("SELECT id,seller_price,seller_stock,is_active FROM product_sellers WHERE id=:id AND seller_id=:seller_id FOR UPDATE"), {"id": listing_id, "seller_id": seller["id"]}).mappings().first()
        if not row:
            return jsonify({"error": "Seller product not found."}), 404
        fields = {}
        if "seller_price" in body:
            try: fields["price"] = Decimal(str(body["seller_price"]))
            except (TypeError, ValueError, ArithmeticError): return jsonify({"error": "Invalid seller_price."}), 400
            if fields["price"] < 0: return jsonify({"error": "Price cannot be negative."}), 400
        if "seller_stock" in body:
            try: fields["stock"] = int(body["seller_stock"])
            except (TypeError, ValueError): return jsonify({"error": "Invalid seller_stock."}), 400
            if fields["stock"] < 0: return jsonify({"error": "Stock cannot be negative."}), 400
        if "is_active" in body:
            if not isinstance(body["is_active"], bool): return jsonify({"error": "is_active must be boolean."}), 400
            fields["active"] = body["is_active"]
        if not fields:
            return jsonify({"error": "No changes supplied."}), 400
        db.execute(text("UPDATE product_sellers SET seller_price=COALESCE(:price,seller_price), seller_stock=COALESCE(:stock,seller_stock), is_active=COALESCE(:active,is_active), updated_at=NOW() WHERE id=:id AND seller_id=:seller_id"), {"price": fields.get("price"), "stock": fields.get("stock"), "active": fields.get("active"), "id": listing_id, "seller_id": seller["id"]})
        updated = db.execute(text("SELECT id,product_id,seller_price,seller_stock,is_active,updated_at FROM product_sellers WHERE id=:id"), {"id": listing_id}).mappings().one()
        db.commit()
    return jsonify({**dict(updated), "seller_price": _money(updated["seller_price"])})


@seller_bp.get("/dashboard")
def seller_dashboard():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        seller = _seller(db, user_id)
        if not seller:
            return jsonify({"error": "Seller profile not found."}), 404
        seller_id = seller["id"]
        listing_count = db.execute(text("SELECT COUNT(*) FROM product_sellers WHERE seller_id=:seller_id AND is_active=TRUE"), {"seller_id": seller_id}).scalar_one()
        order_stats = db.execute(text("""SELECT COUNT(DISTINCT oi.order_id) AS orders, COALESCE(SUM(oi.line_total),0) AS gross_sales,
            COALESCE(SUM(oi.line_total * (1 - :commission_rate / 100)),0) AS seller_earnings
            FROM order_items oi JOIN commerce_orders o ON o.id=oi.order_id
            WHERE oi.seller_id=:seller_id AND o.status NOT IN ('cancelled','refunded')"""), {"seller_id": seller_id, "commission_rate": Decimal(str(seller["commission_rate"] or 0))}).mappings().one()
        status_rows = db.execute(text("""SELECT o.status,COUNT(DISTINCT o.id) AS count FROM commerce_orders o JOIN order_items oi ON oi.order_id=o.id WHERE oi.seller_id=:seller_id GROUP BY o.status ORDER BY o.status"""), {"seller_id": seller_id}).mappings().all()
    return jsonify({"seller": dict(seller), "listing_count": listing_count, "orders": int(order_stats["orders"] or 0), "gross_sales": _money(order_stats["gross_sales"]), "estimated_earnings": _money(order_stats["seller_earnings"]), "order_status": [dict(row) for row in status_rows]})


def register_seller_routes(app):
    if "seller_api" not in app.blueprints:
        app.register_blueprint(seller_bp)
