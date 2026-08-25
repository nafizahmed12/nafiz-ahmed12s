from flask import Blueprint, jsonify, make_response, render_template, session, request
from sqlalchemy import text

from database import SessionLocal
from commerce_routes import _product_row

shop_bp = Blueprint("shop_ui", __name__)


def _category():
    return request.args.get("category", "").strip().lower()


def _shop_response(template, **context):
    category = context.get("category", _category())
    response = make_response(render_template(template, category=category, **{k: v for k, v in context.items() if k != "category"}))
    response.set_cookie("selected_category", category, max_age=3600, httponly=True, samesite="Lax")
    return response


@shop_bp.get("/shop")
def shop():
    return _shop_response("shop.html", category=_category())


@shop_bp.get("/checkout")
def checkout_page():
    category = _category()
    if not session.get("user_id"):
        return _shop_response("shop.html", checkout_requires_login=True, category=category), 401
    return _shop_response("shop.html", checkout_mode=True, category=category)


@shop_bp.get("/payment/success")
def payment_success():
    return render_template(
        "payment_result.html",
        result="success",
        order_id=request.args.get("order_id"),
    )


@shop_bp.get("/payment/fail")
def payment_fail():
    return render_template(
        "payment_result.html",
        result="fail",
        order_id=request.args.get("order_id"),
    )


@shop_bp.get("/payment/cancel")
def payment_cancel():
    return render_template(
        "payment_result.html",
        result="cancel",
        order_id=request.args.get("order_id"),
    )


def _category_products_response():
    if request.path != "/api/products" or request.method != "GET":
        return None

    category = request.args.get("category", "").strip().lower() or request.cookies.get("selected_category", "").strip().lower()
    if not category:
        return None

    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(50, max(1, int(request.args.get("per_page", "20"))))
    except ValueError:
        return jsonify({"error": "Invalid pagination."}), 400

    search = request.args.get("q", "").strip()
    product_type = request.args.get("type", "").strip().lower()
    offset = (page - 1) * per_page
    filters = ["p.status NOT IN ('draft', 'archived')", "LOWER(pc.slug) = :category"]
    params = {"category": category, "limit": per_page, "offset": offset}

    if search:
        filters.append("(p.name ILIKE :search OR p.description ILIKE :search)")
        params["search"] = f"%{search}%"

    if product_type:
        filters.append("p.product_type = :product_type")
        params["product_type"] = product_type

    where_sql = " AND ".join(filters)

    with SessionLocal() as db:
        rows = db.execute(
            text(f"""
                SELECT p.id,p.name,p.slug,p.description,p.product_type,
                       COALESCE(l.price,p.price) AS price,p.currency,p.sku,
                       p.stock_quantity,pi.image_url,l.id AS listing_id,
                       l.price AS listing_price
                FROM products p
                JOIN product_categories pc ON pc.id = p.category_id
                LEFT JOIN LATERAL (
                    SELECT id,price FROM product_listings
                    WHERE product_id=p.id AND status IN ('active','published')
                    ORDER BY featured DESC,id ASC LIMIT 1
                ) l ON TRUE
                LEFT JOIN LATERAL (
                    SELECT image_url FROM product_images
                    WHERE product_id=p.id
                    ORDER BY sort_order ASC,id ASC LIMIT 1
                ) pi ON TRUE
                WHERE {where_sql}
                ORDER BY p.id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()

        total = db.execute(
            text(f"""
                SELECT COUNT(*)
                FROM products p
                JOIN product_categories pc ON pc.id = p.category_id
                WHERE {where_sql}
            """),
            params,
        ).scalar_one()

    return jsonify({
        "items": [_product_row(row) for row in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })


def register_shop_routes(app):
    if shop_bp.name not in app.blueprints:
        app.register_blueprint(shop_bp)
    app.before_request(_category_products_response)
