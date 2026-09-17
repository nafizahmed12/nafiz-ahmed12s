import os
from flask import Blueprint, Response, request

seo_bp = Blueprint("seo", __name__)


def public_base_url():
    return (os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/"))


@seo_bp.get("/seo-sitemap-preview.xml")
def seo_sitemap_preview():
    """Non-invasive SEO sitemap preview for review before production integration."""
    base = public_base_url()
    paths = [
        "/",
        "/shop",
        "/phones",
        "/about",
        "/contact",
        "/privacy-policy",
        "/terms",
        "/refund-policy",
        "/affiliate-picks",
        "/iphone-18",
        "/iphone-18-pro",
        "/iphone-18-pro-max",
        "/iphone-18-series",
        "/iphone-18-comparison",
    ]
    urls = "\n".join(f"  <url><loc>{base}{path}</loc></url>" for path in paths)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        '</urlset>\n'
    )
    return Response(xml, mimetype="application/xml")
