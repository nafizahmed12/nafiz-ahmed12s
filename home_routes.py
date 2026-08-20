from decimal import Decimal

from flask import Blueprint, jsonify, session
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
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "description": row["description"] or "",
            "product_type": row["product_type"],
            "price": _money(row["price"]),
            "compare_at_price": _money(row["compare_at_price"]) if row["compare_at_price"] is not None else None,
            "currency": row["currency"],
            "stock_quantity": row["stock_quantity"],
            "featured": bool(row["featured"]),
            "category": row["category_name"] or "New in",
            "category_slug": row["category_slug"] or "new-in",
            "image_url": row["image_url"],
        })

    return jsonify({
        "products": products,
        "categories": [dict(row) for row in categories],
        "cart_count": int(cart_count or 0),
        "authenticated": bool(user_id),
    })


def register_home_routes(app):
    if home_bp.name not in app.blueprints:
        app.register_blueprint(home_bp)
