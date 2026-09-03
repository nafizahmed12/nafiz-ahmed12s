from decimal import Decimal

from flask import Blueprint, jsonify, request, session, current_app, redirect
from sqlalchemy import text

from database import SessionLocal

home_bp = Blueprint("home_ui", __name__)


def _money(value):
    return format(Decimal(str(value or 0)), ".2f")


@home_bp.get("/api/home")
def home_data():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT p.id, p.name, p.slug, p.description, p.product_type,
                   p.stock_quantity, p.currency,
                   COALESCE(l.price, p.price) AS price,
                   l.compare_at_price, l.featured,
                   c.name AS category_name, c.slug AS category_slug,
                   pi.image_url
            FROM products p
            LEFT JOIN LATERAL (
                SELECT price, compare_at_price, featured
                FROM product_listings
                WHERE product_id = p.id AND status IN ('active','published')
                ORDER BY featured DESC, id ASC LIMIT 1
            ) l ON TRUE
            LEFT JOIN product_categories c ON c.id = p.category_id
            LEFT JOIN LATERAL (
                SELECT image_url
                FROM product_images
                WHERE product_id = p.id
                ORDER BY sort_order ASC, id ASC LIMIT 1
            ) pi ON TRUE
            WHERE p.status NOT IN ('draft','archived')
            ORDER BY COALESCE(l.featured, false) DESC, p.id DESC
            LIMIT 12
        """)).mappings().all()

        categories = db.execute(text("""
            SELECT c.id, c.name, c.slug, COUNT(p.id) AS product_count
            FROM product_categories c
            LEFT JOIN products p ON p.category_id = c.id
                AND p.status NOT IN ('draft','archived')
            GROUP BY c.id, c.name, c.slug
            HAVING COUNT(p.id) > 0
            ORDER BY COUNT(p.id) DESC, c.name ASC
            LIMIT 6
        """)).mappings().all()

        user_id = session.get("user_id")
        cart_count = 0
        if user_id:
            cart_count = db.execute(text("""
                SELECT COALESCE(SUM(ci.quantity), 0)
                FROM carts c JOIN cart_items ci ON ci.cart_id = c.id
                WHERE c.user_id = :user_id
            """), {"user_id": user_id}).scalar_one()

    products = []
    for row in rows:
        products.append({
            "id": row["id"], "name": row["name"], "slug": row["slug"],
            "description": row["description"] or "", "product_type": row["product_type"],
            "price": _money(row["price"]),
            "compare_at_price": _money(row["compare_at_price"]) if row["compare_at_price"] is not None else None,
            "currency": row["currency"], "stock_quantity": row["stock_quantity"],
            "featured": bool(row["featured"]), "category": row["category_name"] or "New in",
            "category_slug": row["category_slug"] or "new-in", "image_url": row["image_url"],
        })

    return jsonify({"products": products, "categories": [dict(row) for row in categories], "cart_count": int(cart_count or 0), "authenticated": bool(user_id)})


@home_bp.get("/api/category-products")
def category_products():
    category = request.args.get("category", "").strip().lower()
    search = request.args.get("q", "").strip()
    product_type = request.args.get("type", "").strip().lower()
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(50, max(1, int(request.args.get("per_page", "20"))))
    except ValueError:
        return jsonify({"error": "Invalid pagination."}), 400
    if not category:
        return jsonify({"error": "Category is required."}), 400

    filters = ["p.status NOT IN ('draft','archived')", "LOWER(c.slug) = :category"]
    params = {"category": category, "limit": per_page, "offset": (page - 1) * per_page}
    if search:
        filters.append("(p.name ILIKE :search OR p.description ILIKE :search)")
        params["search"] = f"%{search}%"
    if product_type:
        filters.append("p.product_type = :product_type")
        params["product_type"] = product_type
    where_sql = " AND ".join(filters)

    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT p.id,p.name,p.slug,p.description,p.product_type,
                   COALESCE(l.price,p.price) AS price,p.currency,p.sku,
                   p.stock_quantity,pi.image_url,l.id AS listing_id,l.price AS listing_price
            FROM products p
            JOIN product_categories c ON c.id = p.category_id
            LEFT JOIN LATERAL (
                SELECT id,price FROM product_listings
                WHERE product_id=p.id AND status IN ('active','published')
                ORDER BY featured DESC,id ASC LIMIT 1
            ) l ON TRUE
            LEFT JOIN LATERAL (
                SELECT image_url FROM product_images
                WHERE product_id=p.id ORDER BY sort_order ASC,id ASC LIMIT 1
            ) pi ON TRUE
            WHERE {where_sql}
            ORDER BY p.id DESC LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = db.execute(text(f"""
            SELECT COUNT(*) FROM products p
            JOIN product_categories c ON c.id = p.category_id
            WHERE {where_sql}
        """), params).scalar_one()

    items = [{
        "id": r["id"], "name": r["name"], "slug": r["slug"], "description": r["description"] or "",
        "product_type": r["product_type"], "price": _money(r["price"]), "currency": r["currency"],
        "sku": r["sku"], "stock_quantity": r["stock_quantity"], "image_url": r["image_url"],
        "listing_id": r["listing_id"], "listing_price": _money(r["listing_price"]) if r["listing_price"] is not None else None,
    } for r in rows]
    return jsonify({"items": items, "page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)})


@home_bp.get("/iphone-18-comparison")
def clean_iphone_18_comparison():
    return current_app.send_static_file("iphone-18-comparison.html")


@home_bp.before_app_request
def redirect_legacy_comparison_url():
    if request.method == "GET" and request.path == "/static/iphone-18-comparison.html":
        return redirect("/iphone-18-comparison", code=301)
    return None


@home_bp.after_app_request
def normalize_comparison_sitemap(response):
    if request.path == "/sitemap.xml" and response.status_code == 200 and "xml" in response.content_type:
        body = response.get_data(as_text=True)
        old = "/static/iphone-18-comparison.html"
        new = "/iphone-18-comparison"
        if old in body:
            body = body.replace(old, new)
        if new not in body:
            close = "</urlset>"
            entry = '<url><loc>' + current_app.config.get("PUBLIC_BASE_URL", "").rstrip("/") + new + '</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
            if current_app.config.get("PUBLIC_BASE_URL") and close in body:
                body = body.replace(close, "  " + entry + "\n" + close)
        response.set_data(body)
    return response


def register_home_routes(app):
    if home_bp.name not in app.blueprints:
        app.register_blueprint(home_bp)
