"""Global phone catalog: searchable, indexable and admin-manageable."""
import csv
import io
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


def _published(where="", params=None, limit=100, offset=0):
    params = dict(params or {})
    params["limit"] = limit
    params["offset"] = offset
    with SessionLocal() as db:
        rows = db.execute(text(f"""SELECT id,brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence
            FROM phone_catalog WHERE status='published' {where}
            ORDER BY published_at DESC NULLS LAST, id DESC LIMIT :limit OFFSET :offset"""), params).mappings().all()
    return [_row(r) for r in rows]


def _published_count(where="", params=None):
    params = dict(params or {})
    with SessionLocal() as db:
        return int(db.execute(text(f"SELECT COUNT(*) FROM phone_catalog WHERE status='published' {where}"), params).scalar_one())


@phone_catalog_bp.get("/phones")
def phones_index():
    q = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = 24
    where, params = [], {}
    if q:
        where.append("(LOWER(brand) LIKE :q OR LOWER(model) LIKE :q OR LOWER(short_description) LIKE :q)")
        params["q"] = f"%{q.lower()}%"
    if brand:
        where.append("LOWER(brand)=:brand")
        params["brand"] = brand.lower()
    clause = ("AND " + " AND ".join(where)) if where else ""
    total = _published_count(clause, params)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        abort(404)
    phones = _published(clause, params, per_page, (page - 1) * per_page)
    with SessionLocal() as db:
        brands = [r[0] for r in db.execute(text("SELECT DISTINCT brand FROM phone_catalog WHERE status='published' ORDER BY brand")).all()]
    return render_template("phones_index.html", phones=phones, brands=brands, q=q, selected_brand=brand, page=page, total_pages=total_pages, total=total)


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
        row = db.execute(text("""SELECT id,brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence
            FROM phone_catalog WHERE slug=:slug AND LOWER(brand)=:brand AND status='published'"""), {"slug": slug, "brand": brand.lower()}).mappings().first()
    if not row:
        abort(404)
    phone = _row(row)
    related = _published("AND LOWER(brand)=:brand AND slug<>:slug", {"brand": brand.lower(), "slug": slug}, 4)
    return render_template("phone_catalog_detail.html", phone=phone, related=related)


@phone_catalog_bp.get("/compare/<left>-vs-<right>")
def phone_compare(left, right):
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT id,brand,model,slug,short_description,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence
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


@phone_catalog_bp.post("/admin/phones/import")
@admin_required
def import_phones():
    """Import a UTF-8 CSV in one transaction; invalid rows are reported and nothing is partially written."""
    upload = request.files.get("csv_file")
    if not upload or not upload.filename:
        flash("Choose a CSV file to import.", "error")
        return redirect(url_for("phone_catalog.admin_phones"))
    try:
        raw = upload.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(raw))
        required = {"brand", "model", "short_description", "content", "specs_json"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            flash("CSV headers must include: brand, model, short_description, content, specs_json.", "error")
            return redirect(url_for("phone_catalog.admin_phones"))
        rows = list(reader)
        if not rows or len(rows) > 500:
            flash("CSV must contain 1–500 data rows.", "error")
            return redirect(url_for("phone_catalog.admin_phones"))
        cleaned, errors, seen = [], [], set()
        for number, raw_row in enumerate(rows, start=2):
            brand = (raw_row.get("brand") or "").strip()
            model = (raw_row.get("model") or "").strip()
            content = (raw_row.get("content") or "").strip()
            description = (raw_row.get("short_description") or "").strip()
            slug = _slug(raw_row.get("slug") or f"{brand}-{model}")
            specs = (raw_row.get("specs_json") or "{}").strip() or "{}"
            status = (raw_row.get("status") or "draft").strip().lower()
            confidence = (raw_row.get("data_confidence") or "unverified").strip().lower()
            source_name = (raw_row.get("source_name") or "").strip()[:120] or None
            source_url = (raw_row.get("source_url") or "").strip()[:2048] or None
            checked_raw = (raw_row.get("source_checked_at") or "").strip()
            checked_at = None
            if checked_raw:
                try:
                    checked_at = datetime.fromisoformat(checked_raw.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Row {number}: source_checked_at must be ISO-8601 (for example 2026-09-09T12:00:00).")
                    continue
            try:
                json.loads(specs)
            except (TypeError, ValueError):
                errors.append(f"Row {number}: specs_json is invalid JSON.")
                continue
            if not brand or not model or not description or len(content) < 80:
                errors.append(f"Row {number}: brand/model/description required and content must be 80+ characters.")
                continue
            if status not in {"draft", "published"}:
                errors.append(f"Row {number}: status must be draft or published.")
                continue
            if confidence not in {"unverified", "verified", "official"}:
                errors.append(f"Row {number}: data_confidence must be unverified, verified, or official.")
                continue
            if status == "published" and confidence == "unverified":
                errors.append(f"Row {number}: published phones must use verified or official data_confidence.")
                continue
            if slug in seen:
                errors.append(f"Row {number}: duplicate slug {slug} inside CSV.")
                continue
            seen.add(slug)
            cleaned.append({"brand": brand[:80], "model": model[:180], "slug": slug, "short_description": description[:320], "content": content, "image_url": (raw_row.get("image_url") or "").strip()[:2048] or None, "release_date": (raw_row.get("release_date") or "").strip()[:40] or None, "price_usd": (raw_row.get("price_usd") or "").strip()[:40] or None, "price_bdt": (raw_row.get("price_bdt") or "").strip()[:40] or None, "specs_json": specs, "seo_description": (raw_row.get("seo_description") or "").strip()[:320], "status": status, "source_name": source_name, "source_url": source_url, "source_checked_at": checked_at, "data_confidence": confidence})
        if errors:
            flash("Import stopped: " + " | ".join(errors[:8]), "error")
            return redirect(url_for("phone_catalog.admin_phones"))
        with SessionLocal() as db:
            existing = {r[0] for r in db.execute(text("SELECT slug FROM phone_catalog WHERE slug = ANY(:slugs)"), {"slugs": [r["slug"] for r in cleaned]}).all()}
            if existing:
                flash("Import stopped: these slugs already exist: " + ", ".join(sorted(existing)[:8]), "error")
                return redirect(url_for("phone_catalog.admin_phones"))
            for item in cleaned:
                db.execute(text("""INSERT INTO phone_catalog (brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,status,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence)
                    VALUES (:brand,:model,:slug,:short_description,:content,:image_url,:release_date,:price_usd,:price_bdt,:specs_json,:status,:seo_description,:published_at,:source_name,:source_url,:source_checked_at,:data_confidence)"""), {**item, "published_at": datetime.utcnow() if item["status"] == "published" else None})
            db.commit()
        flash(f"Imported {len(cleaned)} phone(s) successfully.", "success")
    except UnicodeDecodeError:
        flash("CSV must be UTF-8 encoded.", "error")
    except Exception:
        flash("Import failed safely; no rows were committed. Check the CSV and try again.", "error")
    return redirect(url_for("phone_catalog.admin_phones"))


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
    confidence = request.form.get("data_confidence", "unverified") if request.form.get("data_confidence") in {"unverified", "verified", "official"} else "unverified"
    if status == "published" and confidence == "unverified":
        flash("Published phones must use verified or official data confidence.", "error")
        return redirect(request.referrer or url_for("phone_catalog.admin_phones"))
    checked_raw = request.form.get("source_checked_at", "").strip()
    checked_at = None
    if checked_raw:
        try:
            checked_at = datetime.fromisoformat(checked_raw.replace("Z", "+00:00"))
        except ValueError:
            flash("Source checked time must be ISO-8601.", "error")
            return redirect(request.referrer or url_for("phone_catalog.admin_phones"))
    fields = {"brand": brand[:80], "model": model[:180], "slug": slug, "short_description": description[:320], "content": content, "image_url": request.form.get("image_url", "").strip()[:2048] or None, "release_date": request.form.get("release_date", "").strip()[:40] or None, "price_usd": request.form.get("price_usd", "").strip()[:40] or None, "price_bdt": request.form.get("price_bdt", "").strip()[:40] or None, "specs_json": specs, "seo_description": request.form.get("seo_description", "").strip()[:320], "status": status, "source_name": request.form.get("source_name", "").strip()[:120] or None, "source_url": request.form.get("source_url", "").strip()[:2048] or None, "source_checked_at": checked_at, "data_confidence": confidence}
    with SessionLocal() as db:
        if phone_id is None:
            db.execute(text("""INSERT INTO phone_catalog (brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,status,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence)
                VALUES (:brand,:model,:slug,:short_description,:content,:image_url,:release_date,:price_usd,:price_bdt,:specs_json,:status,:seo_description,:published_at,:source_name,:source_url,:source_checked_at,:data_confidence)"""), {**fields, "published_at": datetime.utcnow() if status == "published" else None})
        else:
            db.execute(text("""UPDATE phone_catalog SET brand=:brand,model=:model,slug=:slug,short_description=:short_description,content=:content,image_url=:image_url,release_date=:release_date,price_usd=:price_usd,price_bdt=:price_bdt,specs_json=:specs_json,status=:status,seo_description=:seo_description,updated_at=CURRENT_TIMESTAMP,published_at=:published_at,source_name=:source_name,source_url=:source_url,source_checked_at=:source_checked_at,data_confidence=:data_confidence WHERE id=:id"""), {**fields, "published_at": datetime.utcnow() if status == "published" else None, "id": phone_id})
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
