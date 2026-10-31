"""Owner-only operational health and integration readiness for the publisher admin."""
import os
import re

from flask import Blueprint, render_template
from sqlalchemy import text

from admin_auth import admin_required
from database import SessionLocal

admin_operations_bp = Blueprint("admin_operations", __name__)

TABLES = {
    "Articles": "blog_articles",
    "Phone catalog": "phone_catalog",
    "Products": "products",
    "Orders": "commerce_orders",
    "Reviews": "product_reviews",
    "Subscribers": "subscribers",
    "Contact messages": "contact_messages",
}


def integration_status():
    """Return configuration booleans only; never expose credentials or secret values."""
    publisher_id = os.getenv("ADSENSE_PUBLISHER_ID", "").strip()
    adsense_configured = bool(re.fullmatch(r"pub-\d{16}", publisher_id))
    ga4_configured = bool(
        os.getenv("GA4_PROPERTY_ID", "").strip()
        and (
            os.getenv("GA4_SERVICE_ACCOUNT_JSON", "").strip()
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        )
    )
    search_console_configured = bool(
        os.getenv("SEARCH_CONSOLE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    return {
        "adsense": {"label": "Google AdSense", "configured": adsense_configured,
                    "detail": "Publisher ID is configured." if adsense_configured else "Set a valid ADSENSE_PUBLISHER_ID."},
        "google_analytics": {"label": "Google Analytics 4", "configured": ga4_configured,
                    "detail": "Property ID and service-account credentials are present." if ga4_configured else "Set GA4_PROPERTY_ID and service-account credentials to enable reporting."},
        "search_console": {"label": "Google Search Console", "configured": search_console_configured,
                    "detail": "Service-account credentials are present." if search_console_configured else "Add Search Console service-account credentials to enable search reporting."},
    }


def _database_health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar_one()
        return {"ok": True, "detail": "Database connection and query succeeded."}
    except Exception:
        # Do not display raw database errors, hostnames, SQL, or credentials in admin HTML.
        return {"ok": False, "detail": "Database connection failed. Check server logs."}


def _content_counts():
    counts = []
    for label, table in TABLES.items():
        try:
            with SessionLocal() as db:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            counts.append({"label": label, "count": int(count), "available": True})
        except Exception:
            counts.append({"label": label, "count": None, "available": False})
    return counts


@admin_operations_bp.get("/admin/operations")
@admin_required
def admin_operations():
    return render_template(
        "admin_operations.html",
        database=_database_health(),
        integrations=integration_status(),
        content_counts=_content_counts(),
        public_base_url_configured=bool(os.getenv("PUBLIC_BASE_URL", "").strip()),
        ads_txt_path="/ads.txt",
        sitemap_path="/sitemap.xml",
        robots_path="/robots.txt",
    )


def register_admin_operations_routes(app):
    if "admin_operations" not in app.blueprints:
        app.register_blueprint(admin_operations_bp)
