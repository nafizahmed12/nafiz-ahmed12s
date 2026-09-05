import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# ----------------------------------------------------
# 1. Flask App Initialization & Config
# ----------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-for-dev")

ADMIN_ROLE = "admin"
ADMIN_IDLE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", "1800"))
ADMIN_ABSOLUTE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200"))
USER_SESSION_CREATED_KEY = "user_session_created_at"

# ----------------------------------------------------
# 2. Database Setup
# ----------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_admin_credentials():
    """Create/sync the bootstrap admin from environment variables."""
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    email = os.getenv("ADMIN_EMAIL", "").strip().lower() or None
    if not username or not password:
        return
    with SessionLocal() as db:
        db.execute(text("""CREATE TABLE IF NOT EXISTS admin_credentials (
            id INTEGER PRIMARY KEY, username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE, password_hash VARCHAR(255) NOT NULL,
            password_changed_at TIMESTAMP WITH TIME ZONE NULL)"""))
        row = db.execute(
            text("SELECT id, username, email FROM admin_credentials ORDER BY id LIMIT 1")
        ).mappings().first()
        if row is None:
            db.execute(
                text("""INSERT INTO admin_credentials
                (id, username, email, password_hash) VALUES (1, :username, :email, :password_hash)"""),
                {"username": username, "email": email, "password_hash": generate_password_hash(password)}
            )
        elif row["username"] != username or (email and row["email"] != email):
            db.execute(
                text("""UPDATE admin_credentials SET username=:username, email=:email WHERE id=:id"""),
                {"username": username, "email": email if email else row["email"], "id": row["id"]}
            )
        db.commit()


# Bandit Fix (B110): try-except pass সরিয়ে নির্দিষ্ট লগিং/হ্যান্ডলিং
try:
    _ensure_admin_credentials()
except Exception as err:
    app.logger.warning("Admin bootstrap skipped or failed: %s", err)

# ----------------------------------------------------
# 3. Dedicated /robots.txt Route (Google Search Console Fix)
# ----------------------------------------------------
@app.route("/robots.txt", methods=["GET"])
def robots_txt():
    site_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /iphone-18\n"
        "Allow: /iphone-18-pro\n"
        "Allow: /iphone-18-pro-max\n"
        "Allow: /iphone-18-series\n"
        "Allow: /iphone-18-comparison\n\n"
        "Disallow: /admin\n"
        "Disallow: /login\n"
        "Disallow: /logout\n"
        "Disallow: /dashboard\n"
        "Disallow: /account\n"
        "Disallow: /register\n"
        "Disallow: /user-login\n"
        "Disallow: /user-logout\n"
        "Disallow: /forgot-password\n"
        "Disallow: /reset-password\n"
        "Disallow: /admin-forgot-password\n"
        "Disallow: /admin-reset-password\n"
        "Disallow: /checkout\n"
        "Disallow: /orders\n"
        "Disallow: /api/\n\n"
        f"Sitemap: {site_url}/sitemap.xml\n"
    )
    resp = Response(content, status=200, mimetype="text/plain")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

# ----------------------------------------------------
# 4. Web & SEO Routes
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html") if os.path.exists("templates/index.html") else "Home Page"

@app.route("/iphone-18-series")
def clean_iphone_18_series():
    return app.send_static_file("iphone-18-series.html")

@app.route("/iphone-18")
def clean_iphone_18():
    return app.send_static_file("iphone-18.html")

@app.route("/iphone-18-pro")
def clean_iphone_18_pro():
    return app.send_static_file("iphone-18-pro.html")

@app.route("/iphone-18-pro-max")
def clean_iphone_18_pro_max():
    return app.send_static_file("iphone-18-pro-max.html")

# ----------------------------------------------------
# 5. Middlewares (before_request & after_request)
# ----------------------------------------------------
@app.before_request
def handle_legacy_iphone_urls():
    redirects = {
        "/static/iphone-18-series.html": "/iphone-18-series",
        "/static/iphone-18.html": "/iphone-18",
        "/static/iphone-18-pro.html": "/iphone-18-pro",
        "/static/iphone-18-pro-max.html": "/iphone-18-pro-max",
    }
    if request.method == "GET" and request.path in redirects:
        return redirect(redirects[request.path], code=301)
    return None

@app.before_request
def handle_legacy_logout_get():
    if request.path != "/user-logout" or request.method != "GET":
        return None
    token = session.get("_csrf_secret")
    if not token:
        token = secrets.token_hex(32)
        session["_csrf_secret"] = token
    return Response(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Confirm logout — Nafiz</title></head><body>"
        "<main style='max-width:520px;margin:12vh auto;padding:24px;font-family:system-ui,sans-serif'>"
        "<h1>Confirm logout</h1><p>Are you sure you want to sign out?</p>"
        "<form method='post' action='/user-logout'>"
        f"<input type='hidden' name='csrf_token' value='{token}'>"
        "<button type='submit'>Sign out</button></form></main></body></html>",
        status=200, mimetype="text/html",
    )

@app.after_request
def rewrite_iphone_seo_urls(response):
    if request.path in {"/iphone-18-series", "/iphone-18", "/iphone-18-pro", "/iphone-18-pro-max"} and response.status_code == 200 and "text/html" in response.content_type:
        response.direct_passthrough = False
        body = response.get_data(as_text=True)
        replacements = {
            "/static/iphone-18-series.html": "/iphone-18-series",
            "/static/iphone-18-pro-max.html": "/iphone-18-pro-max",
            "/static/iphone-18-pro.html": "/iphone-18-pro",
            "/static/iphone-18.html": "/iphone-18",
        }
        for old, new in replacements.items():
            body = body.replace(old, new)
        response.set_data(body)
    return response

@app.after_request
def harden_content_security_policy(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'; img-src 'self' data: https:; font-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https:; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; media-src 'self' https:; worker-src 'self'; manifest-src 'self';"
    )
    return response

# ----------------------------------------------------
# 6. Auth Helpers & App Entry Point
# ----------------------------------------------------
def mark_admin_authenticated(username):
    configured_username = os.getenv("ADMIN_USERNAME", "").strip()
    if not configured_username or not username or not hmac.compare_digest(str(username).strip(), configured_username):
        raise ValueError("Configured admin identity mismatch.")
    now = datetime.now(timezone.utc).timestamp()
    session["admin_logged_in"] = True
    session["admin_role"] = ADMIN_ROLE
    session["admin_username"] = configured_username
    session["admin_authenticated_at"] = now
    session["admin_last_activity"] = now

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Bandit Fix (B201): debug=True ডায়নামিক করা
    is_debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=is_debug)
