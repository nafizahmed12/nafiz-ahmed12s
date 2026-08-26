import hmac
import logging
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
from bkash_routes import register_bkash_routes
from seller_routes import register_seller_routes
from digital_affiliate_routes import register_digital_affiliate_routes
from shop_routes import register_shop_routes
from admin_product_routes import register_admin_product_routes
from admin_security import register_admin_session_guard, mark_admin_authenticated, clear_admin_session
from admin_auth import admin_required
from csrf import register_csrf_protection
from mail_utils import send_password_reset_email
from schema import (
    allow_contact, allow_login, allow_registration, allow_subscription,
    allow_password_reset, authenticate_user, change_password, create_message,
    create_password_reset_token, create_subscriber, create_user, create_website,
    delete_website, get_admin_stats, get_messages, get_subscribers, get_user,
    get_user_websites, get_website_by_slug, reset_password_with_token,
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
register_bkash_routes(app)
register_seller_routes(app)
register_digital_affiliate_routes(app)
register_shop_routes(app)
register_admin_product_routes(app)
register_admin_session_guard(app)
register_csrf_protection(app)

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
    sensitive_paths = ("/dashboard", "/account", "/admin", "/login", "/user-login", "/forgot-password", "/reset-password")
    if any(request.path == path or request.path.startswith(f"{path}/") for path in sensitive_paths):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.before_request
def protect_state_changing_requests():
    if request.method != "POST":
        return None
    if request.path.startswith("/api/payments/sslcommerz/"):
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

@app.route("/favicon.ico")
def favicon_ico():
    return redirect(url_for("static", filename="favicon.svg"), code=301)

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
Disallow: /forgot-password
Disallow: /reset-password

Sitemap: https://nafiz-ahmed12s.onrender.com/sitemap.xml
"""
    return Response(content, mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap_xml():
    site_url = url_for("home", _external=True)
    content = f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>{site_url}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n'''
    return Response(content, mimetype="application/xml")

@app.route("/")
def home():
    host_slug = get_host_site_slug()
    if host_slug:
        website = get_website_by_slug(host_slug)
        if website:
            return render_template("published_site.html", website=website)
        abort(404)
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if not allow_registration(request.remote_addr, limit=10, window_seconds=3600):
            return render_template("register.html", error="Too many registration attempts from this network. Please try again later."), 429
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3 or len(username) > 80:
            return render_template("register.html", error="Username must be 3-80 characters."), 400
        if not valid_email(email):
            return render_template("register.html", error="Enter a valid email address."), 400
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters."), 400
        if password != confirm:
            return render_template("register.html", error="Passwords do not match."), 400
        user = create_user(username, email, password)
        if user is None:
            return render_template("register.html", error="Username or email is already in use."), 409
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["username"] = user.username
        flash("Account created successfully. Welcome!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/user-login", methods=["GET", "POST"])
def user_login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not allow_login(request.remote_addr, identifier, limit=10, window_seconds=900):
            return render_template("user_login.html", error="Too many login attempts. Please try again in a few minutes."), 429
        user = authenticate_user(identifier, password)
        if user is None:
            return render_template("user_login.html", error="Invalid username/email or password."), 401
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["username"] = user.username
        session["user_session_created_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp()
        flash("Logged in successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("user_login.html")

@app.route("/dashboard")
def dashboard():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    return render_template("dashboard.html", user=user, websites=get_user_websites(user.id))

@app.route("/dashboard/websites", methods=["POST"])
def create_website_route():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    description = request.form.get("description", "").strip()
    if not name or not slug:
        flash("Website name and slug are required.", "error")
        return redirect(url_for("dashboard"))
    if len(name) > 120 or len(slug) > 80 or not all(c.isalnum() or c == "-" for c in slug):
        flash("Invalid website name or slug.", "error")
        return redirect(url_for("dashboard"))
    website = create_website(user.id, name, slug, description)
    flash("Website created successfully." if website else "Could not create website.", "success" if website else "error")
    return redirect(url_for("dashboard"))

@app.route("/dashboard/websites/<int:website_id>/delete", methods=["POST"])
def delete_website_route(website_id):
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    deleted = delete_website(user.id, website_id)
    flash("Website deleted successfully." if deleted else "Website not found or you do not have permission to delete it.", "success" if deleted else "error")
    return redirect(url_for("dashboard"))

@app.route("/account", methods=["GET", "POST"])
def account():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "profile":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            if len(username) < 3 or len(username) > 80:
                flash("Username must be 3-80 characters.", "error")
                return redirect(url_for("account"))
            if not valid_email(email):
                flash("Enter a valid email address.", "error")
                return redirect(url_for("account"))
            ok, msg = update_user_profile(user.id, username, email)
            if ok:
                session["username"] = username
            flash(msg, "success" if ok else "error")
            return redirect(url_for("account"))
        if action == "password":
            cur = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if new != confirm:
                flash("New passwords do not match.", "error")
                return redirect(url_for("account"))
            ok, msg = change_password(user.id, cur, new)
            flash(msg, "success" if ok else "error")
            return redirect(url_for("account"))
    return render_template("account.html", user=get_user(user.id))

@app.route("/orders")
def orders_page():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    return render_template("orders.html", user=user)

@app.route("/payment/<result>")
def payment_result_page(result):
    if result not in {"success", "fail", "cancel"}:
        abort(404)
    return render_template("payment_result.html", result=result, order_id=request.args.get("order_id"))

@app.route("/site/<slug>")
def published_site(slug):
    website = get_website_by_slug(slug)
    if website is None:
        abort(404)
    return render_template("published_site.html", website=website)

@app.route("/user-logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("_permanent", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("user_login"))

@app.route("/contact", methods=["POST"])
def contact():
    if not allow_contact(request.remote_addr, limit=5, window_seconds=900):
        return "Too many messages from this network. Please try again later.", 429
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    message = request.form.get("message", "").strip()
    if len(name) < 2 or len(name) > 120:
        return "Name must be between 2 and 120 characters.", 400
    if not valid_email(email):
        return "Enter a valid email address.", 400
    if len(message) < 5 or len(message) > 5000:
        return "Message must be between 5 and 5000 characters.", 400
    create_message(name, email, message)
    return "Message saved successfully!"

@app.route("/subscribe", methods=["POST"])
def subscribe():
    if not allow_subscription(request.remote_addr, limit=10, window_seconds=3600):
        return "Too many subscription attempts. Please try again later.", 429
    email = request.form.get("subscriber_email", "").strip().lower()
    if not valid_email(email):
        return "Enter a valid email address.", 400
    if create_subscriber(email):
        return "Subscribed successfully!"
    return "This email is already subscribed!", 409

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not allow_login(request.remote_addr, f"admin:{username}", limit=5, window_seconds=900):
            return "Too many admin login attempts. Please try again in a few minutes.", 429
        configured_username = os.getenv("ADMIN_USERNAME", "")
        configured_password = os.getenv("ADMIN_PASSWORD", "")
        supplied_password = request.form.get("password", "")
        if configured_username and configured_password and hmac.compare_digest(username, configured_username) and hmac.compare_digest(supplied_password, configured_password):
            session.clear()
            session.permanent = True
            mark_admin_authenticated()
            return redirect(url_for("admin"))
        return "Invalid username or password.", 401
    return render_template("login.html")

@app.route("/admin")
@admin_required
def admin():
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = 50
    stats = get_admin_stats()
    messages, total = get_messages(page=page, per_page=per_page)
    subscribers, total_subscribers = get_subscribers(page=page, per_page=per_page)
    return render_template("admin.html", stats=stats, messages=messages, subscribers=subscribers, page=page, total_pages=max(1, (total + per_page - 1) // per_page), subscriber_pages=max(1, (total_subscribers + per_page - 1) // per_page))

@app.route("/logout")
def logout():
    clear_admin_session()
    return redirect(url_for("login"))

if __name__ == "__main__":
    from database import init_db
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
