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
def redesign_home_page(response):
    if request.path != "/" or response.status_code != 200 or "text/html" not in response.content_type:
        return response
    response.direct_passthrough = False
    body = response.get_data(as_text=True)
    css = '''<style id="nafiz-home-redesign">
:root{--home-bg:#f5f7fb;--home-surface:#fff;--home-ink:#111827;--home-muted:#6b7280;--home-line:#e5e7eb;--home-brand:#111827;--home-accent:#ff5a36;--home-accent2:#ff8a4c}
html{background:var(--home-bg)!important}body{background:var(--home-bg)!important;color:var(--home-ink)!important;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important}
.top{height:32px!important;background:#111827!important;color:#d1d5db!important;border:0!important;font-size:10px!important}.top b{color:#fff!important}
.nav{height:76px!important;background:rgba(255,255,255,.96)!important;border:0!important;border-bottom:1px solid var(--home-line)!important;position:sticky!important;top:0!important;z-index:60!important;box-shadow:0 5px 22px rgba(17,24,39,.05)!important}
.logo{font-size:22px!important;color:#111827!important}.logo span{color:var(--home-accent)!important}.links{gap:22px!important}.links a{color:#4b5563!important;font-size:12px!important}.links a:hover{color:#111827!important}
.nav-btn{background:#fff!important;border:1px solid var(--home-line)!important;color:#111827!important;border-radius:12px!important}.count{background:var(--home-accent)!important}
main.wrap{max-width:1240px!important}.search-row{padding:22px 0 8px!important}.search{height:50px!important;background:#fff!important;border:1px solid #dfe3ea!important;color:#111827!important;border-radius:14px!important;box-shadow:0 5px 18px rgba(17,24,39,.04)!important}.search::placeholder{color:#9ca3af!important}.filter{background:#fff!important;border-color:#dfe3ea!important;color:#111827!important}
.categories{padding:10px 0 8px!important;gap:8px!important}.pill{background:#fff!important;border:1px solid #e1e5eb!important;color:#4b5563!important;padding:10px 17px!important;border-radius:10px!important}.pill.active{background:#111827!important;color:#fff!important;box-shadow:none!important}
.hero{margin-top:14px!important;min-height:330px!important;border:0!important;border-radius:24px!important;background:linear-gradient(120deg,#111827 0%,#1f2937 58%,#3a241d 100%)!important;box-shadow:0 20px 50px rgba(17,24,39,.16)!important}.hero-copy{padding:50px!important}.eyebrow{color:#d1d5db!important}.hero h1{font-size:clamp(38px,5vw,62px)!important;color:#fff!important}.hero h1 span{background:linear-gradient(90deg,#fff,#ffad7b)!important;-webkit-background-clip:text!important}.hero p{color:#cbd5e1!important;font-size:13px!important;max-width:500px!important}.cta{background:var(--home-accent)!important;box-shadow:0 12px 28px rgba(255,90,54,.25)!important;border-radius:11px!important}.hero-visual{background:radial-gradient(circle at 50% 50%,#3f2c25,#18202c 65%)!important}.sale{background:var(--home-accent)!important}
.section{padding-top:38px!important}.section-head{margin-bottom:17px!important}.section-head h2{font-size:24px!important;color:#111827!important}.section-head span{color:#6b7280!important}
.cards{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:18px!important;overflow:visible!important;padding:2px 1px 6px!important}.card{min-width:0!important;background:#fff!important;border:1px solid #e5e7eb!important;border-radius:18px!important;padding:9px!important;box-shadow:0 8px 24px rgba(17,24,39,.05)!important}.card:hover{transform:translateY(-5px)!important;border-color:#d1d5db!important;box-shadow:0 18px 38px rgba(17,24,39,.10)!important}.pic{height:255px!important;background:#f7f8fa!important;border-radius:13px!important}.pic img{padding:18px!important}.hot{background:var(--home-accent)!important}.heart{background:#fff!important;border-color:#e5e7eb!important;color:#374151!important}.card-body{padding:12px 5px 5px!important}.type{color:#9ca3af!important}.card h3{color:#111827!important;font-size:14px!important}.sub{color:#6b7280!important}.money{color:#111827!important}.plus{background:#111827!important;color:#fff!important}.plus:hover{background:var(--home-accent)!important}
.promo{margin-top:40px!important;border:0!important;border-radius:22px!important;background:#111827!important;box-shadow:0 18px 42px rgba(17,24,39,.13)!important}.promo-copy h2{color:#fff!important}.promo-copy p{color:#cbd5e1!important}.promo-copy small{color:#ff9a78!important}.time{background:#1f2937!important;border-color:#374151!important}.time b{color:#fff!important}.time span{color:#9ca3af!important}.promo-art{background:radial-gradient(circle,#3d2a22,#111827 68%)!important}
.news{padding:58px 0!important}.news h2{color:#111827!important}.news p{color:#6b7280!important}.form{background:#fff!important;border-color:#e5e7eb!important}.form input{color:#111827!important}.form button{background:var(--home-accent)!important}
.footer{background:#111827!important;border:0!important;color:#9ca3af!important;padding:44px 0 80px!important;margin-top:10px!important}.footer strong{color:#fff!important}.footer h4{color:#e5e7eb!important}.footer a{color:#9ca3af!important}.copyright{border-color:#374151!important}
.home-affiliate-section{margin-top:40px!important;background:#fff!important;border:1px solid #e5e7eb!important;border-radius:22px!important;box-shadow:0 10px 28px rgba(17,24,39,.05)!important}.home-affiliate-head h2{color:#111827!important}.home-affiliate-head p,.home-affiliate-disclosure{color:#6b7280!important}.home-affiliate-card{background:#fff!important;border-color:#e5e7eb!important;box-shadow:0 7px 20px rgba(17,24,39,.04)!important}.home-affiliate-image{background:#f7f8fa!important}.home-affiliate-body h3{color:#111827!important}.home-affiliate-body p{color:#6b7280!important}.home-affiliate-price{color:#111827!important}.home-affiliate-bottom a{background:var(--home-accent)!important}
.bottom-cart{background:rgba(255,255,255,.96)!important;border-color:#e5e7eb!important;box-shadow:0 10px 28px rgba(17,24,39,.15)!important}.bottom-cart .bagmini{background:#111827!important}.bottom-cart .total{color:#111827!important}.bottom-cart a{background:var(--home-accent)!important}.bottom-nav{background:rgba(255,255,255,.98)!important;border-color:#e5e7eb!important}.bottom-nav a{color:#6b7280!important}.bottom-nav a b{color:#374151!important}.bottom-nav a.active,.bottom-nav a.active b{color:var(--home-accent)!important}
@media(max-width:1000px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))!important}.hero-copy{padding:38px!important}}
@media(max-width:760px){.nav{height:64px!important}.cards{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:12px!important}.pic{height:220px!important}.hero{grid-template-columns:1fr!important}.hero-copy{padding:32px 24px!important}.hero-visual{min-height:220px!important}.promo{grid-template-columns:1fr!important}.promo-art{min-height:180px!important}}
@media(max-width:600px){.wrap{width:calc(100% - 20px)!important}.top{font-size:8px!important}.logo{font-size:18px!important}.search-row{padding-top:13px!important}.categories{padding-top:8px!important}.section{padding-top:28px!important}.section-head h2{font-size:20px!important}.cards{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:9px!important}.card{border-radius:15px!important;padding:7px!important}.pic{height:185px!important}.pic img{padding:12px!important}.card-body{padding:9px 3px 3px!important}.card h3{font-size:12px!important}.money{font-size:13px!important}.plus{width:31px!important}.hero h1{font-size:37px!important}.hero-copy{padding:28px 20px!important}.hero p{font-size:11px!important}.promo-copy{padding:27px 20px!important}.footer-grid{grid-template-columns:1fr 1fr!important}}
</style>'''
    if "</head>" in body and "nafiz-home-redesign" not in body:
        body = body.replace("</head>", css + "</head>", 1)
        response.set_data(body)
    return response


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
                LIMIT 4
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
