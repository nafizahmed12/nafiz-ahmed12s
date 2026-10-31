"""Editorial administration dashboard and SEO audit tools."""
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import text

from admin_auth import admin_required
from database import SessionLocal

publisher_admin_bp = Blueprint("publisher_admin", __name__)


def _count(db, table, where=""):
    # Table names and predicates are fixed constants owned by this module.
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table} {where}")).scalar_one())


def normalize_seo_metadata(form, title, excerpt):
    """Validate and normalize editable article SEO/social metadata."""
    seo_title = (form.get("seo_title") or "").strip() or (title or "").strip()
    canonical_url = (form.get("canonical_url") or "").strip()
    og_title = (form.get("og_title") or "").strip() or seo_title
    og_description = (form.get("og_description") or "").strip() or (excerpt or "").strip()
    if len(seo_title) > 200:
        raise ValueError("SEO title must be 200 characters or fewer.")
    if len(og_title) > 200:
        raise ValueError("Open Graph title must be 200 characters or fewer.")
    if len(og_description) > 320:
        raise ValueError("Open Graph description must be 320 characters or fewer.")
    if len(canonical_url) > 2048:
        raise ValueError("Canonical URL is too long.")
    if canonical_url:
        parsed = urlsplit(canonical_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Canonical URL must be a valid HTTP or HTTPS URL.")
    return {
        "seo_title": seo_title,
        "canonical_url": canonical_url or None,
        "og_title": og_title,
        "og_description": og_description,
    }


def audit_article_seo(article):
    """Return actionable metadata issues for one article without changing it."""
    description = (article.get("seo_description") or "").strip()
    issues = []
    if not description:
        issues.append("Missing SEO description")
    elif len(description) < 120:
        issues.append("SEO description too short")
    elif len(description) > 160:
        issues.append("SEO description too long")
    if not (article.get("excerpt") or "").strip():
        issues.append("Missing excerpt")
    if not (article.get("featured_image_url") or "").strip():
        issues.append("Missing featured image")
    return issues


@publisher_admin_bp.get("/admin/publisher")
@admin_required
def publisher_dashboard():
    with SessionLocal() as db:
        stats = {
            "articles_total": _count(db, "blog_articles"),
            "articles_published": _count(db, "blog_articles", "WHERE status='published'"),
            "articles_drafts": _count(db, "blog_articles", "WHERE status='draft'"),
            "phones_total": _count(db, "phone_catalog"),
            "phones_published": _count(db, "phone_catalog", "WHERE status='published'"),
            "phones_drafts": _count(db, "phone_catalog", "WHERE status='draft'"),
        }
        latest_articles = db.execute(text("""
            SELECT id, title, slug, status, updated_at
            FROM blog_articles
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 8
        """)).mappings().all()
    return render_template(
        "admin_publisher_dashboard.html",
        stats=stats,
        latest_articles=latest_articles,
    )


@publisher_admin_bp.get("/admin/seo")
@admin_required
def publisher_seo_manager():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, title, slug, excerpt, featured_image_url,
                   seo_description, seo_title, canonical_url, og_title, og_description, status
            FROM blog_articles
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 200
        """)).mappings().all()
    articles = []
    for row in rows:
        article = dict(row)
        article["seo_issues"] = audit_article_seo(article)
        article["canonical_path"] = f"/blog/{article.get('slug') or ''}"
        articles.append(article)
    return render_template(
        "admin_publisher_seo.html",
        articles=articles,
        issue_count=sum(bool(article["seo_issues"]) for article in articles),
        sitemap_url="/sitemap.xml",
    )


def normalize_bulk_article_action(action):
    """Allow only the three explicitly supported bulk operations."""
    action = (action or "").strip().lower()
    return action if action in {"publish", "draft", "delete"} else None


def normalize_bulk_article_ids(values):
    """Parse unique positive article IDs, rejecting oversized submissions."""
    values = list(values or [])
    if len(values) > 100:
        return []
    article_ids = []
    for value in values:
        try:
            article_id = int(value)
        except (TypeError, ValueError):
            continue
        if article_id > 0 and article_id not in article_ids:
            article_ids.append(article_id)
    return article_ids


@publisher_admin_bp.route("/admin/bulk", methods=["GET", "POST"])
@admin_required
def publisher_bulk_editor():
    if request.method == "POST":
        action = normalize_bulk_article_action(request.form.get("action"))
        article_ids = normalize_bulk_article_ids(request.form.getlist("article_ids"))
        if not action or not article_ids:
            flash("Choose a valid action and at least one article (maximum 100).", "error")
            return redirect(url_for("publisher_admin.publisher_bulk_editor"))

        placeholders = ", ".join(f":id_{index}" for index in range(len(article_ids)))
        params = {f"id_{index}": value for index, value in enumerate(article_ids)}
        with SessionLocal() as db:
            if action == "delete":
                result = db.execute(
                    text(f"DELETE FROM blog_articles WHERE id IN ({placeholders})"),
                    params,
                )
            elif action == "publish":
                params["published_at"] = datetime.now(timezone.utc)
                result = db.execute(
                    text(f"""
                        UPDATE blog_articles
                        SET status = 'published',
                            published_at = COALESCE(published_at, :published_at),
                            updated_at = :published_at
                        WHERE id IN ({placeholders})
                    """),
                    params,
                )
            else:
                params["updated_at"] = datetime.now(timezone.utc)
                result = db.execute(
                    text(f"""
                        UPDATE blog_articles
                        SET status = 'draft', published_at = NULL,
                            updated_at = :updated_at
                        WHERE id IN ({placeholders})
                    """),
                    params,
                )
            affected = result.rowcount or 0
            db.commit()
        flash(f"{affected} article(s) processed.", "success")
        return redirect(url_for("publisher_admin.publisher_bulk_editor"))

    with SessionLocal() as db:
        articles = db.execute(text("""
            SELECT id, title, slug, status, updated_at
            FROM blog_articles
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 200
        """)).mappings().all()
    return render_template("admin_publisher_bulk.html", articles=articles)


def register_publisher_admin_routes(app):
    if "publisher_admin" not in app.blueprints:
        app.register_blueprint(publisher_admin_bp)
