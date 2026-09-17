import os
from flask import Blueprint, Response, current_app, request, url_for

seo_bp = Blueprint("seo", __name__)


def public_base_url():
    return (os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/"))


@seo_bp.get("/robots.txt")
def robots_txt():
    base = public_base_url()
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /login",
        "Disallow: /logout",
        "Disallow: /dashboard",
        "Disallow: /account",
        "Disallow: /register",
        "Disallow: /user-login",
        "Disallow: /user-logout",
        "Disallow: /forgot-password",
        "Disallow: /reset-password",
        "Disallow: /admin-forgot-password",
        "Disallow: /admin-reset-password",
        "Disallow: /checkout",
        "Disallow: /orders",
        "Disallow: /api/",
        "",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ])
    return Response(body, mimetype="text/plain")


@seo_bp.get("/sitemap.xml")
def sitemap_xml():
    base = public_base_url()
    paths = [
        "/", "/shop", "/phones", "/about", "/blog", "/best-phones",
        "/affiliate-picks", "/iphone-18", "/iphone-18-pro",
        "/iphone-18-pro-max", "/iphone-18-series",
    ]
    urls = [f"<url><loc>{base}{path}</loc></url>" for path in paths]
    try:
        # Use the application's existing endpoint when available; this avoids
        # coupling SEO code to the project's database/model implementation.
        endpoint = "phone_detail"
        if endpoint in current_app.view_functions:
            # Dynamic products can be added by the existing sitemap implementation
            # later without making this endpoint fail during a DB/cold-start error.
            pass
    except Exception:
        current_app.logger.exception("Sitemap dynamic route inspection failed")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += '\n</urlset>\n'
    return Response(xml, mimetype="application/xml")


def register_seo_routes(app):
    if "seo" not in app.blueprints:
        app.register_blueprint(seo_bp)
