from hashlib import sha256
from secrets import token_urlsafe
from decimal import Decimal

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal

bp = Blueprint("digital_affiliate_api", __name__, url_prefix="/api")


def _uid():
    try:
        return int(session.get("user_id")) if session.get("user_id") is not None else None
    except (TypeError, ValueError):
        return None


def _money(v):
    return format(Decimal(str(v or 0)), ".2f")


@bp.post("/digital-products")
def create_digital_product():
    uid = _uid()
    if uid is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    slug = str(body.get("slug", "")).strip().lower()
    description = str(body.get("description", "")).strip()
    delivery_url = str(body.get("delivery_url", "")).strip() or None
    file_name = str(body.get("file_name", "")).strip() or None
    try:
        price = Decimal(str(body.get("price", "0")))
    except Exception:
        return jsonify({"error": "Invalid price."}), 400
    if not name or not slug or price < 0:
        return jsonify({"error": "name, slug and a non-negative price are required."}), 400
    if len(slug) > 180:
        return jsonify({"error": "Slug is too long."}), 400
    with SessionLocal() as db:
        try:
            product_id = db.execute(text("""INSERT INTO products (name,slug,description,product_type,price,currency,sku,stock_quantity,status,created_at,updated_at) VALUES (:name,:slug,:description,'digital',:price,'BDT',:sku,0,'published',NOW(),NOW()) RETURNING id"""), {"name": name, "slug": slug, "description": description, "price": price, "sku": "DIG-" + token_urlsafe(8)}).scalar_one()
            db.execute(text("""INSERT INTO digital_products (product_id,owner_user_id,delivery_url,file_name,created_at,updated_at) VALUES (:product_id,:uid,:url,:file,NOW(),NOW())"""), {"product_id": product_id, "uid": uid, "url": delivery_url, "file": file_name})
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"error": "That product slug is already in use."}), 409
    return jsonify({"product_id": product_id, "name": name, "slug": slug, "price": _money(price), "product_type": "digital"}), 201


@bp.get("/digital-products/mine")
def my_digital_products():
    uid = _uid()
    if uid is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT p.id,p.name,p.slug,p.price,p.currency,dp.delivery_url,dp.file_name,dp.version,dp.is_active FROM digital_products dp JOIN products p ON p.id=dp.product_id WHERE dp.owner_user_id=:uid ORDER BY dp.id DESC"""), {"uid": uid}).mappings().all()
    return jsonify({"items": [{"id": r["id"], "name": r["name"], "slug": r["slug"], "price": _money(r["price"]), "currency": r["currency"], "delivery_url": r["delivery_url"], "file_name": r["file_name"], "version": r["version"], "is_active": r["is_active"]} for r in rows]})


@bp.post("/affiliate/join")
def join_affiliate():
    uid = _uid()
    if uid is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        existing = db.execute(text("SELECT id,code,commission_rate,status FROM affiliate_profiles WHERE user_id=:uid"), {"uid": uid}).mappings().first()
        if existing:
            return jsonify(dict(existing))
        code = "naf-" + token_urlsafe(8).replace("-", "a").replace("_", "b")
        db.execute(text("INSERT INTO affiliate_profiles (user_id,code,commission_rate,status,created_at,updated_at) VALUES (:uid,:code,10,'active',NOW(),NOW())"), {"uid": uid, "code": code})
        db.commit()
        row = db.execute(text("SELECT id,code,commission_rate,status FROM affiliate_profiles WHERE user_id=:uid"), {"uid": uid}).mappings().one()
    return jsonify({**dict(row), "affiliate_url": request.host_url.rstrip("/") + "/?ref=" + row["code"]}), 201


@bp.get("/affiliate/me")
def affiliate_me():
    uid = _uid()
    if uid is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        row = db.execute(text("SELECT id,code,commission_rate,status FROM affiliate_profiles WHERE user_id=:uid"), {"uid": uid}).mappings().first()
        if not row:
            return jsonify({"error": "Affiliate profile not found."}), 404
        stats = db.execute(text("""SELECT COUNT(DISTINCT c.id) AS clicks, COUNT(DISTINCT cv.id) AS conversions, COALESCE(SUM(cv.commission_amount),0) AS earnings FROM affiliate_profiles a LEFT JOIN affiliate_clicks c ON c.affiliate_id=a.id LEFT JOIN affiliate_conversions cv ON cv.affiliate_id=a.id WHERE a.id=:aid"""), {"aid": row["id"]}).mappings().one()
    return jsonify({"affiliate": dict(row), "affiliate_url": request.host_url.rstrip("/") + "/?ref=" + row["code"], "clicks": stats["clicks"], "conversions": stats["conversions"], "earnings": _money(stats["earnings"])})


@bp.post("/affiliate/click")
def affiliate_click():
    body = request.get_json(silent=True) or {}
    code = str(body.get("code", "")).strip()
    if not code:
        return jsonify({"error": "Affiliate code is required."}), 400
    with SessionLocal() as db:
        affiliate = db.execute(text("SELECT id FROM affiliate_profiles WHERE code=:code AND status='active'"), {"code": code}).scalar_one_or_none()
        if affiliate is None:
            return jsonify({"error": "Affiliate code not found."}), 404
        product_id = body.get("product_id")
        try:
            product_id = int(product_id) if product_id is not None else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid product_id."}), 400
        visitor = str(body.get("visitor_key", "")).strip()[:128] or None
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = sha256(ip.encode()).hexdigest()
        db.execute(text("INSERT INTO affiliate_clicks (affiliate_id,product_id,visitor_key,ip_hash,user_agent,created_at) VALUES (:aid,:pid,:visitor,:ip,:ua,NOW())"), {"aid": affiliate, "pid": product_id, "visitor": visitor, "ip": ip_hash, "ua": request.headers.get("User-Agent", "")[:500]})
        db.commit()
    return jsonify({"tracked": True}), 201


def register_digital_affiliate_routes(app):
    app.register_blueprint(bp)
