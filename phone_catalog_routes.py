"""Global phone catalog: searchable, indexable and admin-manageable."""
import json
import re
from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from database import SessionLocal
from admin_auth import admin_required

phone_catalog_bp = Blueprint("phone_catalog", __name__)


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return value[:220]


def _row(row):
    if not row:
        return None
    item = dict(row)
    try:
        item["specs"] = json.loads(item.get("specs_json") or "{}")
    except (TypeError, ValueError):
        item["specs"] = {}
    return item


def _published(where="", params=None, limit=100):
    params = dict(params or {})
    params["limit"] = limit
    with SessionLocal() as db:
        rows = db.execute(text(f"""SELECT id,brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at
            FROM phone_catalog WHERE status='published' {where}
            ORDER BY published_at DESC NULLS LAST, id DESC LIMIT :limit"""), params).mappings().all()
    return [_row(r) for r in rows]


@phone_catalog_bp.get("/phones")
def phones_index():
    q = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    where, params = [], {}
    if q:
        where.append("(LOWER(brand) LIKE :q OR LOWER(model) LIKE :q OR LOWER(short_description) LIKE :q)")
        params["q"] = f"%{q.lower()}%"
    if brand:
        where.append("LOWER(brand)=:brand")
        params["brand"] = brand.lower()
    clause = ("AND " + " AND ".join(where)) if where else ""
    phones = _published(clause, params, 100)
    with SessionLocal() as db:
        brands = [r[0] for r in db.execute(text("SELECT DISTINCT brand FROM phone_catalog WHERE status='published' ORDER BY brand")).all()]
    return render_template("phones_index.html", phones=phones, brands=brands, q=q, selected_brand=brand)


@phone_catalog_bp.get("/phones/<brand>")
def phone_brand(brand):
    phones = _published("AND LOWER(brand)=:brand", {"brand": brand.lower()}, 100)
    if not phones:
        abort(404)
    canonical_brand = phones[0]["brand"]
    return render_template("phone_brand.html", phones=phones, brand=canonical_brand)


@phone_catalog_bp.get("/phones/<brand>/<slug>")
def phone_catalog_detail(brand, slug):
    with SessionLocal() as db:
        row = db.execute(text("""SELECT id,brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at
            FROM phone_catalog WHERE slug=:slug AND LOWER(brand)=:brand AND status='published'"""), {"slug": slug, "brand": brand.lower()}).mappings().first()
    if not row:
        abort(404)
    phone = _row(row)
    related = _published("AND LOWER(brand)=:brand AND slug<>:slug", {"brand": brand.lower(), "slug": slug}, 4)
    return render_template("phone_catalog_detail.html", phone=phone, related=related)


@phone_catalog_bp.get("/compare/<left>-vs-<right>")
def phone_compare(left, right):
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT id,brand,model,slug,short_description,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at
            FROM phone_catalog WHERE slug IN (:left,:right) AND status='published'"""), {"left": left, "right": right}).mappings().all()
    phones = {_row(r)["slug"]: _row(r) for r in rows}
    if left not in phones or right not in phones:
        abort(404)
    return render_template("phone_compare.html", left=phones[left], right=phones[right])


@phone_catalog_bp.get("/admin/phones")
@admin_required
def admin_phones():
    with SessionLocal() as db:
        phones = db.execute(text("SELECT * FROM phone_catalog ORDER BY id DESC LIMIT 200")).mappings().all()
    return render_template("admin_phones.html", phones=[_row(r) for r in phones], editing=None)


@phone_catalog_bp.post("/admin/phones")
@admin_required
def create_phone():
    return _save_phone(None)


@phone_catalog_bp.get("/admin/phones/<int:phone_id>/edit")
@admin_required
def edit_phone(phone_id):
    with SessionLocal() as db:
        row = db.execute(text("SELECT * FROM phone_catalog WHERE id=:id"), {"id": phone_id}).mappings().first()
        phones = db.execute(text("SELECT * FROM phone_catalog ORDER BY id DESC LIMIT 200")).mappings().all()
    if not row:
        abort(404)
    return render_template("admin_phones.html", phones=[_row(r) for r in phones], editing=_row(row))


@phone_catalog_bp.post("/admin/phones/<int:phone_id>/edit")
@admin_required
def update_phone(phone_id):
    return _save_phone(phone_id)


def _save_phone(phone_id):
    brand = request.form.get("brand", "").strip()
    model = request.form.get("model", "").strip()
    slug = _slug(request.form.get("slug") or f"{brand}-{model}")
    description = request.form.get("short_description", "").strip()
    content = request.form.get("content", "").strip()
    specs = request.form.get("specs_json", "{}").strip() or "{}"
    try:
        json.loads(specs)
    except ValueError:
        flash("Specs must be valid JSON.", "error")
        return redirect(request.referrer or url_for("phone_catalog.admin_phones"))
    if not brand or not model or not description or len(content) < 80:
        flash("Brand, model, description and at least 80 characters of useful content are required.", "error")
        return redirect(request.referrer or url_for("phone_catalog.admin_phones"))
    status = request.form.get("status", "draft") if request.form.get("status") in {"draft", "published"} else "draft"
    fields = {
        "brand": brand[:80], "model": model[:180], "slug": slug, "short_description": description[:320],
        "content": content, "image_url": request.form.get("image_url", "").strip()[:2048] or None,
        "release_date": request.form.get("release_date", "").strip()[:40] or None,
        "price_usd": request.form.get("price_usd", "").strip()[:40] or None,
        "price_bdt": request.form.get("price_bdt", "").strip()[:40] or None,
        "specs_json": specs, "seo_description": request.form.get("seo_description", "").strip()[:320], "status": status,
    }
    with SessionLocal() as db:
        if phone_id is None:
            db.execute(text("""INSERT INTO phone_catalog (brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,status,seo_description,published_at)
                VALUES (:brand,:model,:slug,:short_description,:content,:image_url,:release_date,:price_usd,:price_bdt,:specs_json,:status,:seo_description,:published_at)"""), {**fields, "published_at": datetime.utcnow() if status == "published" else None})
        else:
            db.execute(text("""UPDATE phone_catalog SET brand=:brand,model=:model,slug=:slug,short_description=:short_description,content=:content,image_url=:image_url,release_date=:release_date,price_usd=:price_usd,price_bdt=:price_bdt,specs_json=:specs_json,status=:status,seo_description=:seo_description,updated_at=CURRENT_TIMESTAMP,published_at=:published_at WHERE id=:id"""), {**fields, "published_at": datetime.utcnow() if status == "published" else None, "id": phone_id})
        db.commit()
    flash("Phone saved.", "success")
    return redirect(url_for("phone_catalog.admin_phones"))


@phone_catalog_bp.post("/admin/phones/<int:phone_id>/delete")
@admin_required
def delete_phone(phone_id):
    with SessionLocal() as db:
        db.execute(text("DELETE FROM phone_catalog WHERE id=:id"), {"id": phone_id})
        db.commit()
    flash("Phone deleted.", "success")
    return redirect(url_for("phone_catalog.admin_phones"))


def register_phone_catalog_routes(app):
    app.register_blueprint(phone_catalog_bp)
