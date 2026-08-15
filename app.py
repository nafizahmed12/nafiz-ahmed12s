import os
from datetime import timedelta
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, session, abort, flash, url_for
from dotenv import load_dotenv

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


@app.after_request
def add_security_headers(response):
    """Add baseline browser security headers without changing the existing UI."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )

    # Only advertise HSTS when the request is actually HTTPS. This avoids
    # accidentally pinning a local HTTP development environment.
    if request.is_secure:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.before_request
def protect_state_changing_requests():
    """Reject cross-site browser POST requests before they reach application logic."""
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
            return render_template(
                "register.html",
                error="Too many registration attempts from this network. Please try again later.",
            ), 429

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 80:
            return render_template("register.html", error="Username must be 3-80 characters."), 400
        if not valid_email(email):
            return render_template("register.html", error="Enter a valid email address."), 400
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters."), 400
        if password != confirm_password:
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
            return render_template(
                "user_login.html",
                error="Too many login attempts. Please try again in a few minutes.",
            ), 429

        user = authenticate_user(identifier, password)
        if user is None:
            return render_template("user_login.html", error="Invalid username/email or password."), 401

        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["username"] = user.username
        flash("Welcome back!", "success")
        return redirect(url_for("dashboard"))

    return render_template("user_login.html")


@app.route("/dashboard")
def dashboard():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))
    websites = get_user_websites(user.id)
    return render_template("dashboard.html", user=user, username=user.username, websites=websites)


@app.route("/dashboard/websites", methods=["POST"])
def create_website_route():
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))

    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    title = request.form.get("title", "My Website").strip()
    content = request.form.get("content", "").strip()

    if not name or not slug or not title:
        flash("Name, slug and title are required.", "error")
        return redirect(url_for("dashboard"))
    if not all(c.isalnum() or c == "-" for c in slug) or slug.startswith("-") or slug.endswith("-"):
        flash("Slug may contain only letters, numbers and hyphens.", "error")
        return redirect(url_for("dashboard"))

    website = create_website(user.id, name, slug, title, content)
    if website is None:
        flash("That slug is already taken. Choose another one.", "error")
        return redirect(url_for("dashboard"))

    flash("Website created successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/websites/<int:website_id>/delete", methods=["POST"])
def delete_website_route(website_id):
    user = require_user()
    if user is None:
        return redirect(url_for("user_login"))

    if delete_website(user.id, website_id):
        flash("Website deleted successfully.", "success")
    else:
        flash("Website not found or you do not have permission to delete it.", "error")
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
            ok, message = update_user_profile(user.id, username, email)
            if ok:
                session["username"] = username
            flash(message, "success" if ok else "error")
            return redirect(url_for("account"))

        if action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("account"))
            ok, message = change_password(user.id, current_password, new_password)
            flash(message, "success" if ok else "error")
            return redirect(url_for("account"))

    user = get_user(user.id)
    return render_template("account.html", user=user)


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

        if username == os.getenv("ADMIN_USERNAME") and request.form.get("password", "") == os.getenv("ADMIN_PASSWORD"):
            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return "Invalid username or password.", 401
    return render_template("login.html")


@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    per_page = 50
    stats = get_admin_stats()
    messages, total = get_messages(page=page, per_page=per_page)
    subscribers, total_subscribers = get_subscribers(page=page, per_page=per_page)

    total_pages = max(1, (total + per_page - 1) // per_page)
    subscriber_pages = max(1, (total_subscribers + per_page - 1) // per_page)
    max_page = max(total_pages, subscriber_pages)
    if page > max_page:
        page = max_page
        messages, total = get_messages(page=page, per_page=per_page)
        subscribers, total_subscribers = get_subscribers(page=page, per_page=per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)
        subscriber_pages = max(1, (total_subscribers + per_page - 1) // per_page)

    return render_template(
        "admin.html",
        stats=stats,
        messages=messages,
        page=page,
        total_pages=total_pages,
        total_messages=total,
        subscribers=subscribers,
        total_subscribers=total_subscribers,
        subscriber_pages=subscriber_pages,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
