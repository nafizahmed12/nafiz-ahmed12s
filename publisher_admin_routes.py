"""Editorial administration dashboard for the technology publisher."""
from flask import Blueprint, render_template
from sqlalchemy import text

from admin_auth import admin_required
from database import SessionLocal

publisher_admin_bp = Blueprint("publisher_admin", __name__)


def _count(db, table, where=""):
    # Table names and predicates are fixed constants owned by this module.
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table} {where}")).scalar_one())


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


def register_publisher_admin_routes(app):
    if "publisher_admin" not in app.blueprints:
        app.register_blueprint(publisher_admin_bp)
