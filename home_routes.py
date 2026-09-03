from decimal import Decimal
from html import escape

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
def add_home_affiliate_products(response):
    if request.path != "/" or response.status_code != 200 or "text/html" not in response.content_type:
        return response

    try:
        with SessionLocal() as db:
            rows = db.execute(text("""
                SELECT id,name,description,amazon_url,image_url,display_price
                FROM affiliate_products
                WHERE status='published'
                ORDER BY sort_order ASC,id DESC
            """)).mappings().all()
    except Exception:
        current_app.logger.exception("Failed to load home affiliate products")
        return response

    if not rows:
        return response

    response.direct_passthrough = False
    body = response.get_data(as_text=True)
    cards = []
    for row in rows:
        name = escape(row["name"] or "Recommended product")
        description = escape(row["description"] or "Check details and compatibility before purchase.")
        amazon_url = escape(row["amazon_url"] or "#", quote=True)
        image_url = escape(row["image_url"] or "", quote=True)
        display_price = escape(row["display_price"] or "", quote=True)
        image_html = f'<img src="{image_url}" alt="{name}" loading="lazy">' if image_url else '<div class="home-affiliate-no-image">Amazon</div>'
        price_html = f'<span class="home-affiliate-price">{display_price}</span>' if display_price else ''
        cards.append(
            f'<article class="home-affiliate-card"><div class="home-affiliate-image">{image_html}</div>'
            f'<div class="home-affiliate-body"><h3>{name}</h3><p>{description}</p>'
            f'<div class="home-affiliate-bottom">{price_html}<a href="{amazon_url}" target="_blank" rel="noopener noreferrer sponsored">Check on Amazon →</a></div></div></article>'
        )

    section = f'''<section class="home-affiliate-section wrap" aria-labelledby="home-affiliate-title">
<style>
.home-affiliate-section{{margin-top:36px;padding:26px;border:1px solid #292f40;border-radius:23px;background:linear-gradient(135deg,#111722,#171222)}}
.home-affiliate-head{{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:16px}}
.home-affiliate-head h2{{margin:0;font-size:22px;letter-spacing:-.035em}}
.home-affiliate-head p{{margin:5px 0 0;color:#858da2;font-size:11px}}
.home-affiliate-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}
.home-affiliate-card{{background:#0e1119;border:1px solid #292f40;border-radius:18px;overflow:hidden}}
.home-affiliate-image{{height:190px;background:#151a25;display:grid;place-items:center}}
.home-affiliate-image img{{width:100%;height:100%;object-fit:contain;padding:14px}}
.home-affiliate-no-image{{color:#858da2;font-size:12px}}
.home-affiliate-body{{padding:13px}}
.home-affiliate-body h3{{margin:0 0 6px;font-size:13px;line-height:1.4;color:#f5f6fb}}
.home-affiliate-body p{{margin:0;color:#858da2;font-size:10px;line-height:1.55;min-height:32px}}
.home-affiliate-bottom{{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:13px}}
.home-affiliate-price{{font-weight:800;font-size:12px}}
.home-affiliate-bottom a{{padding:9px 10px;border-radius:10px;background:linear-gradient(135deg,#35a7ff,#9a4cff);font-size:9px;font-weight:700;color:#fff;white-space:nowrap}}
.home-affiliate-disclosure{{margin:13px 0 0;color:#70798e;font-size:9px}}
@media(max-width:850px){{.home-affiliate-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:600px){{.home-affiliate-section{{margin-top:28px;padding:20px 12px;border-radius:19px}}.home-affiliate-grid{{grid-template-columns:1fr 1fr;gap:10px}}.home-affiliate-image{{height:155px}}.home-affiliate-body{{padding:10px}}.home-affiliate-bottom a{{font-size:8px;padding:8px}}}}
</style>
<div class="home-affiliate-head"><div><h2 id="home-affiliate-title">Recommended Accessories</h2><p>Useful picks from Amazon</p></div><a href="/affiliate-picks" style="font-size:10px;color:#a765ff;font-weight:700">View all →</a></div>
<div class="home-affiliate-grid">{"".join(cards)}</div>
<p class="home-affiliate-disclosure">As an Amazon Associate, Nafiz -Ecommerce earns from qualifying purchases.</p>
</section>'''

    if "</main>" not in body:
        return response
    body = body.replace("</main>", section + "</main>", 1)
    response.set_data(body)
    return response


@home_bp.after_app_request
def normalize_comparison_sitemap(response):
    if request.path == "/sitemap.xml" and response.status_code == 200 and "xml" in response.content_type:
        body = response.get_data(as_text=True)
        old = "/static/iphone-18-comparison.html"
        new = "/iphone-18-comparison"
        if old in body:
            body = body.replace(old, new)
        if new not in body and "</urlset>" in body:
            base = request.host_url.rstrip("/")
            entry = f'<url><loc>{base}{new}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
            body = body.replace("</urlset>", "  " + entry + "\n</urlset>")
        response.set_data(body)
    return response


def register_home_routes(app):
    if home_bp.name not in app.blueprints:
        app.register_blueprint(home_bp)
