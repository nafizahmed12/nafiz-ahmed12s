"""Owner-only editorial workflow tools: media, scheduling, revisions, activity and settings."""
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, abort, current_app, flash, has_request_context, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from sqlalchemy import text

from admin_auth import admin_required
from database import SessionLocal

admin_editorial_bp = Blueprint("admin_editorial", __name__)

ARTICLE_SNAPSHOT_FIELDS = (
    "id", "title", "slug", "excerpt", "content", "category",
    "featured_image_url", "seo_description", "status",
    "created_at", "updated_at", "published_at", "scheduled_at",
)
SITE_SETTING_LIMITS = {
    "site_title": 120,
    "site_tagline": 180,
    "site_description": 320,
}
DEFAULT_SITE_SETTINGS = {
    "site_title": "NafizTech",
    "site_tagline": "Mobile, Gadgets, AI and Technology News",
    "site_description": "NafizTech covers mobile technology, gadgets, artificial intelligence, and technology news for readers worldwide.",
}
MEDIA_MAX_BYTES = 900 * 1024
IMAGE_SIGNATURES = {
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ".gif": ("image/gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    ".webp": ("image/webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


def cloudinary_storage_configured():
    """Return whether the Cloudinary credentials needed for persistent uploads exist."""
    if os.getenv("CLOUDINARY_URL", "").strip():
        return True
    return all(os.getenv(key, "").strip() for key in (
        "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"
    ))


def _configure_cloudinary():
    import cloudinary

    cloudinary_url = os.getenv("CLOUDINARY_URL", "").strip()
    if cloudinary_url:
        cloudinary.config()
    else:
        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"].strip(),
            api_key=os.environ["CLOUDINARY_API_KEY"].strip(),
            api_secret=os.environ["CLOUDINARY_API_SECRET"].strip(),
            secure=True,
        )
    return cloudinary


def upload_image_to_cloudinary(raw, filename):
    """Upload validated image bytes and return Cloudinary's public ID and HTTPS URL."""
    if not cloudinary_storage_configured():
        raise RuntimeError("Cloudinary storage is not configured.")
    cloudinary = _configure_cloudinary()
    from cloudinary import uploader

    folder = os.getenv("CLOUDINARY_FOLDER", "nafiztech/media").strip().strip("/") or "nafiztech/media"
    result = uploader.upload(
        io.BytesIO(raw),
        resource_type="image",
        folder=folder,
        public_id=Path(filename).stem,
        overwrite=False,
        unique_filename=False,
        use_filename=False,
        filename_override=filename,
    )
    public_id = str(result.get("public_id") or "").strip()
    secure_url = str(result.get("secure_url") or "").strip()
    parsed_url = urlsplit(secure_url)
    if not public_id or parsed_url.scheme != "https" or not parsed_url.netloc:
        raise RuntimeError("Cloudinary did not return a valid public ID and secure HTTPS URL.")
    return {"public_id": public_id, "secure_url": secure_url}


def delete_cloudinary_image(public_id):
    """Delete a previously uploaded Cloudinary image by its stored public ID."""
    if not cloudinary_storage_configured():
        raise RuntimeError("Cloudinary storage is not configured.")
    _configure_cloudinary()
    from cloudinary import uploader

    return uploader.destroy(public_id, resource_type="image", invalidate=True)


def normalize_schedule_datetime(value, now=None, timezone_name=None):
    """Parse a local datetime input, interpret it in the configured site timezone and return UTC."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Choose a publication date and time.")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Enter a valid publication date and time.") from exc
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name or os.getenv("SITE_TIMEZONE", "Asia/Dhaka")))
        except ZoneInfoNotFoundError as exc:
            raise ValueError("The configured site timezone is invalid.") from exc
    parsed = parsed.astimezone(timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    if parsed <= reference.astimezone(timezone.utc):
        raise ValueError("Scheduled publication must be in the future.")
    return parsed


def format_schedule_input(value):
    """Format a stored UTC timestamp for the datetime-local editor in the site timezone."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    zone = ZoneInfo(os.getenv("SITE_TIMEZONE", "Asia/Dhaka"))
    return value.astimezone(zone).strftime("%Y-%m-%dT%H:%M")


def format_schedule_display(value):
    """Format scheduled publication time in the configured site timezone."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    zone = ZoneInfo(os.getenv("SITE_TIMEZONE", "Asia/Dhaka"))
    return value.astimezone(zone).strftime("%d %b %Y, %H:%M")


def normalize_site_settings(payload):
    """Accept only explicitly supported public-facing settings; ignore secrets and unknown keys."""
    clean = {}
    for key, limit in SITE_SETTING_LIMITS.items():
        value = str((payload or {}).get(key, "")).strip()
        if len(value) > limit:
            raise ValueError(f"{key.replace('_', ' ').title()} must be {limit} characters or fewer.")
        clean[key] = value
    if not clean["site_title"]:
        raise ValueError("Site title is required.")
    return clean


def validate_media_upload(filename, mime_type, raw):
    suffix = Path(secure_filename(filename or "")).suffix.lower()
    signature = IMAGE_SIGNATURES.get(suffix)
    if not signature:
        raise ValueError("Only JPG, PNG, GIF and WEBP images are supported.")
    expected_mime, checker = signature
    if (mime_type or "").lower() != expected_mime or not checker(raw or b""):
        raise ValueError("The file extension, MIME type and image content do not match.")
    if not raw:
        raise ValueError("The selected image is empty.")
    if len(raw) > MEDIA_MAX_BYTES:
        raise ValueError("Images must be 900 KB or smaller.")
    return {"extension": suffix, "mime_type": expected_mime}


def build_article_snapshot(article):
    snapshot = {}
    for key in ARTICLE_SNAPSHOT_FIELDS:
        if key not in article:
            continue
        value = article[key]
        snapshot[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return snapshot


def record_article_revision(db, article, note="Article updated"):
    snapshot = build_article_snapshot(article)
    db.execute(
        text("""INSERT INTO article_revisions (article_id,snapshot_json,revision_note,actor,created_at)
            VALUES (:article_id,:snapshot,:note,:actor,:created_at)"""),
        {
            "article_id": int(article["id"]),
            "snapshot": json.dumps(snapshot, ensure_ascii=False),
            "note": note[:200],
            "actor": str(actor or "scheduler")[:120],
            "created_at": datetime.now(timezone.utc),
        },
    )


def log_admin_activity(db, action, entity_type, entity_id=None, summary=""):
    actor = session.get("admin_username") if has_request_context() else None
    db.execute(
        text("""INSERT INTO admin_activity_log (actor,action,entity_type,entity_id,summary,created_at)
            VALUES (:actor,:action,:entity_type,:entity_id,:summary,:created_at)"""),
        {
            "actor": str(actor or "scheduler")[:120],
            "action": str(action)[:80],
            "entity_type": str(entity_type)[:80],
            "entity_id": entity_id,
            "summary": str(summary)[:500],
            "created_at": datetime.now(timezone.utc),
        },
    )


def publish_due_articles(db, now=None):
    now = now or datetime.now(timezone.utc)
    result = db.execute(
        text("""UPDATE blog_articles
            SET status='published', published_at=scheduled_at, scheduled_at=NULL, updated_at=:now
            WHERE status='scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= :now"""),
        {"now": now},
    )
    if result.rowcount:
        log_admin_activity(db, "scheduled_publish", "article", None, f"Published {result.rowcount} scheduled article(s).")
        db.commit()
    return result.rowcount or 0


def get_public_site_settings():
    try:
        with SessionLocal() as db:
            rows = db.execute(text("SELECT setting_key,setting_value FROM site_settings")).mappings().all()
        if not rows:
            return None
        settings = dict(DEFAULT_SITE_SETTINGS)
        for row in rows:
            if row["setting_key"] in SITE_SETTING_LIMITS:
                settings[row["setting_key"]] = row["setting_value"]
        return settings
    except Exception:
        current_app.logger.exception("Could not load public site settings")
        return None


@admin_editorial_bp.get("/admin/media")
@admin_required
def media_library():
    with SessionLocal() as db:
        media = db.execute(text("""SELECT id,filename,original_name,mime_type,size_bytes,alt_text,uploaded_by,created_at
            FROM admin_media ORDER BY created_at DESC,id DESC LIMIT 300""")).mappings().all()
    return render_template("admin_media_library.html", media=media)


@admin_editorial_bp.post("/admin/media/upload")
@admin_required
def upload_media():
    uploaded = request.files.get("image")
    if not uploaded or not uploaded.filename:
        flash("Choose an image to upload.", "error")
        return redirect(url_for("admin_editorial.media_library"))
    raw = uploaded.read(MEDIA_MAX_BYTES + 1)
    try:
        info = validate_media_upload(uploaded.filename, uploaded.mimetype, raw)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_editorial.media_library"))
    if not cloudinary_storage_configured():
        flash("Cloudinary is not configured. Add CLOUDINARY_URL in Render Environment before uploading media.", "error")
        return redirect(url_for("admin_editorial.media_library"))

    filename = f"{uuid.uuid4().hex}{info['extension']}"
    alt_text = request.form.get("alt_text", "").strip()[:300]
    cloud_asset = None
    try:
        cloud_asset = upload_image_to_cloudinary(raw, filename)
        with SessionLocal() as db:
            db.execute(text("""INSERT INTO admin_media
                (filename,original_name,mime_type,size_bytes,alt_text,uploaded_by,created_at,
                 storage_provider,storage_key,secure_url)
                VALUES (:filename,:original_name,:mime_type,:size_bytes,:alt_text,:uploaded_by,:created_at,
                 'cloudinary',:storage_key,:secure_url)"""),
                {"filename": filename, "original_name": secure_filename(uploaded.filename)[:255],
                 "mime_type": info["mime_type"], "size_bytes": len(raw), "alt_text": alt_text,
                 "uploaded_by": str(session.get("admin_username") or "admin")[:120],
                 "created_at": datetime.now(timezone.utc),
                 "storage_key": cloud_asset["public_id"], "secure_url": cloud_asset["secure_url"]})
            log_admin_activity(db, "media_upload", "media", None, f"Uploaded image {filename} to Cloudinary.")
            db.commit()
    except Exception:
        if cloud_asset:
            try:
                delete_cloudinary_image(cloud_asset["public_id"])
            except Exception:
                current_app.logger.exception("Cloudinary cleanup failed after media database error")
        current_app.logger.exception("Media upload could not be saved to Cloudinary")
        flash("Image could not be saved to Cloudinary. Check the storage configuration and try again.", "error")
        return redirect(url_for("admin_editorial.media_library"))
    flash("Image uploaded successfully to Cloudinary.", "success")
    return redirect(url_for("admin_editorial.media_library"))


@admin_editorial_bp.get("/media/<path:filename>")
def serve_media(filename):
    if not re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|jpeg|png|gif|webp)", filename):
        abort(404)
    with SessionLocal() as db:
        media = db.execute(text("""SELECT storage_provider,storage_key,secure_url
            FROM admin_media WHERE filename=:filename"""), {"filename": filename}).mappings().first()
    if media is None:
        abort(404)
    if media["storage_provider"] == "cloudinary":
        secure_url = str(media["secure_url"] or "").strip()
        parsed_url = urlsplit(secure_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            abort(404)
        return redirect(secure_url, code=302)
    upload_dir = Path(os.getenv("MEDIA_UPLOAD_DIR", str(Path(current_app.root_path) / "static" / "uploads"))).resolve()
    return send_from_directory(upload_dir, filename, conditional=True, max_age=31536000)


@admin_editorial_bp.post("/admin/media/<int:media_id>/delete")
@admin_required
def delete_media(media_id):
    with SessionLocal() as db:
        row = db.execute(text("SELECT filename,storage_provider,storage_key FROM admin_media WHERE id=:id"), {"id": media_id}).mappings().first()
        if row is None:
            abort(404)
        filename = row["filename"]
        if row["storage_provider"] == "cloudinary":
            try:
                result = delete_cloudinary_image(row["storage_key"])
                if result.get("result") not in {"ok", "not found"}:
                    raise RuntimeError("Cloudinary did not confirm image deletion.")
            except Exception:
                current_app.logger.exception("Cloudinary media deletion failed")
                flash("Image could not be deleted from Cloudinary. The media record was kept.", "error")
                return redirect(url_for("admin_editorial.media_library"))
        db.execute(text("DELETE FROM admin_media WHERE id=:id"), {"id": media_id})
        log_admin_activity(db, "media_delete", "media", media_id, f"Deleted image {filename}.")
        db.commit()
    if row["storage_provider"] != "cloudinary":
        upload_dir = Path(os.getenv("MEDIA_UPLOAD_DIR", str(Path(current_app.root_path) / "static" / "uploads"))).resolve()
        (upload_dir / filename).unlink(missing_ok=True)
    flash("Media item deleted.", "success")
    return redirect(url_for("admin_editorial.media_library"))


@admin_editorial_bp.post("/api/internal/publish-scheduled")
def publish_scheduled_api():
    configured_token = os.getenv("SCHEDULED_PUBLISH_TOKEN", "").strip()
    supplied = request.headers.get("Authorization", "")
    token = supplied[7:].strip() if supplied.startswith("Bearer ") else ""
    import hmac
    if not configured_token:
        return jsonify({"error": "Scheduled publishing token is not configured."}), 503
    if not token or not hmac.compare_digest(token, configured_token):
        return jsonify({"error": "Unauthorized"}), 401
    with SessionLocal() as db:
        published = publish_due_articles(db)
    return jsonify({"published": published}), 200


@admin_editorial_bp.get("/admin/schedule")
@admin_required
def editorial_schedule():
    with SessionLocal() as db:
        publish_due_articles(db)
        articles = db.execute(text("""SELECT id,title,slug,status,scheduled_at
            FROM blog_articles WHERE status='scheduled'
            ORDER BY scheduled_at ASC,id ASC LIMIT 200""")).mappings().all()
    display_articles = [dict(row, scheduled_at_display=format_schedule_display(row["scheduled_at"])) for row in articles]
    return render_template("admin_schedule.html", articles=display_articles)


@admin_editorial_bp.get("/admin/articles/<int:article_id>/history")
@admin_required
def article_history(article_id):
    with SessionLocal() as db:
        article = db.execute(text("SELECT id,title FROM blog_articles WHERE id=:id"), {"id": article_id}).mappings().first()
        if article is None:
            abort(404)
        revisions = db.execute(text("""SELECT id,revision_note,actor,created_at
            FROM article_revisions WHERE article_id=:id ORDER BY created_at DESC,id DESC LIMIT 100"""),
            {"id": article_id}).mappings().all()
    return render_template("admin_article_history.html", article=article, revisions=revisions)


@admin_editorial_bp.post("/admin/articles/<int:article_id>/history/<int:revision_id>/restore")
@admin_required
def restore_article_revision(article_id, revision_id):
    with SessionLocal() as db:
        current = db.execute(text("SELECT * FROM blog_articles WHERE id=:id"), {"id": article_id}).mappings().first()
        revision = db.execute(text("""SELECT snapshot_json FROM article_revisions
            WHERE id=:revision_id AND article_id=:article_id"""),
            {"revision_id": revision_id, "article_id": article_id}).mappings().first()
        if current is None or revision is None:
            abort(404)
        record_article_revision(db, current, "Before restoring an older revision")
        snapshot = json.loads(revision["snapshot_json"])
        fields = ("title","slug","excerpt","content","category","featured_image_url","seo_description","status","published_at","scheduled_at")
        params = {key: snapshot.get(key) for key in fields}
        params["id"] = article_id
        params["updated_at"] = datetime.now(timezone.utc)
        db.execute(text("""UPDATE blog_articles SET title=:title,slug=:slug,excerpt=:excerpt,content=:content,
            category=:category,featured_image_url=:featured_image_url,seo_description=:seo_description,
            status=:status,published_at=:published_at,scheduled_at=:scheduled_at,updated_at=:updated_at WHERE id=:id"""), params)
        log_admin_activity(db, "article_revision_restore", "article", article_id, f"Restored revision #{revision_id}.")
        db.commit()
    flash("Article revision restored.", "success")
    return redirect(url_for("admin_editorial.article_history", article_id=article_id))


@admin_editorial_bp.get("/admin/activity")
@admin_required
def admin_activity():
    action = request.args.get("action", "").strip()[:80]
    with SessionLocal() as db:
        if action:
            rows = db.execute(text("""SELECT id,actor,action,entity_type,entity_id,summary,created_at
                FROM admin_activity_log WHERE action=:action ORDER BY created_at DESC,id DESC LIMIT 250"""),
                {"action": action}).mappings().all()
        else:
            rows = db.execute(text("""SELECT id,actor,action,entity_type,entity_id,summary,created_at
                FROM admin_activity_log ORDER BY created_at DESC,id DESC LIMIT 250""")).mappings().all()
    return render_template("admin_activity.html", entries=rows, selected_action=action)


@admin_editorial_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_site_settings():
    if request.method == "POST":
        try:
            values = normalize_site_settings(request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin_editorial.admin_site_settings"))
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            for key, value in values.items():
                db.execute(text("""INSERT INTO site_settings(setting_key,setting_value,updated_by,updated_at)
                    VALUES(:key,:value,:actor,:now)
                    ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,
                    updated_by=excluded.updated_by,updated_at=excluded.updated_at"""),
                    {"key": key, "value": value, "actor": str(session.get("admin_username") or "admin")[:120], "now": now})
            log_admin_activity(db, "site_settings_update", "site_settings", None, "Updated public site title and description settings.")
            db.commit()
        flash("Site settings saved.", "success")
        return redirect(url_for("admin_editorial.admin_site_settings"))
    values = dict(DEFAULT_SITE_SETTINGS)
    with SessionLocal() as db:
        rows = db.execute(text("SELECT setting_key,setting_value FROM site_settings")).mappings().all()
    values.update({row["setting_key"]: row["setting_value"] for row in rows if row["setting_key"] in SITE_SETTING_LIMITS})
    return render_template("admin_site_settings.html", settings=values)


def register_admin_editorial_routes(app):
    if "admin_editorial" not in app.blueprints:
        app.register_blueprint(admin_editorial_bp)
