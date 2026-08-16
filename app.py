import os
from datetime import timedelta
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, session, abort, flash, url_for, Response
from dotenv import load_dotenv
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from database import SessionLocal
from error_handlers import register_error_handlers
from commerce_routes import register_commerce_routes
from payment_routes import register_payment_routes
from supplier_routes import register_supplier_routes
from schema import (
    allow_contact,
    allow_login,
    allow_registration,
    allow_subscription,
    authenticate_user,
    change_password,
    create_message,
    create_subscriber,
    create_user,
    create_website,
    delete_website,
    get_admin_stats,
    get_messages,
    get_subscribers,
    get_user,
    get_user_websites,
    get_website_by_slug,
    update_user_profile,
)

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    if os.getenv("RENDER"):
        raise RuntimeError("SECRET_KEY environment variable is required in production.")
    secret_key = "dev-only-change-this-secret"
app.secret_key = secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "1" if os.getenv("RENDER") else "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH", str(1 * 1024 * 1024))),
)
register_error_handlers(app)
register_commerce_routes(app)
register_payment_routes(app)
register_supplier_routes(app)


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data: https:; font-src 'self' data: https:; style-src 'self' 'unsafe-inline' https:; script-src 'self' 'unsafe-inline' https:; connect-src 'self' https:; media-src 'self' https:;")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.after_request
def prevent_sensitive_page_caching(response):
    sensitive_paths = ("/dashboard", "/account", "/admin", "/login", "/user-login")
    if any(request.path == path or request.path.startswith(f"{path}/") for path in sensitive_paths):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.before_request
def protect_state_changing_requests():
    if request.method != "POST":
        return None
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    expected = f"{request.scheme}://{request.host}"
    source = origin or referer
    if source:
        parsed = urlparse(source)
        actual = f"{parsed.scheme}://{parsed.netloc}"
        if actual != expected:
            abort(403, description="Cross-site request blocked.")
    return None


def get_host_site_slug():
    base_domain = os.getenv("BASE_DOMAIN", "").strip().lower().rstrip(".")
    host = request.host.split(":", 1)[0].lower().rstrip(".")
    if not base_domain or host in {base_domain, f"www.{base_domain}"}:
        return None
    suffix = f".{base_domain}"
    if host.endswith(suffix):
        slug = host[:-len(suffix)]
        if slug and "." not in slug:
            return slug
    return None


def current_user():
    user_id = session.get("user_id")
    return get_user(user_id) if user_id else None


def require_user():
    user = current_user()
    if user is None:
        session.pop("user_id", None)
        session.pop("username", None)
        return None
    return user


def valid_email(email):
    email = (email or "").strip()
    if len(email) > 255 or email.count("@") != 1:
        return False
    local, domain = email.rsplit("@", 1)
    return bool(local and domain and "." in domain and not any(c.isspace() for c in email))


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/health/ready")
def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}, 200
    except Exception:
        app.logger.exception("Readiness check failed")
        return {"status": "not_ready", "database": "unavailable"}, 503


@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /
Disallow: /admin
Disallow: /login
Disallow: /logout
Disallow: /dashboard
Disallow: /account
Disallow: /register
Disallow: /user-login
Disallow: /user-logout

Sitemap: https://nafiz-ahmed12s.onrender.com/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    site_url = url_for("home", _external=True)
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{site_url}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
</urlset>
'''
    return Response(content, mimetype="application/xml")


@app.route("/")
def home():
    host_slug = get_host_site_slug()
    if host_slug:
        website = get_website_by_slug(host_slug)
        if website:
            return render_template("published_site.html", website=website)
    return render_template("index.html")
