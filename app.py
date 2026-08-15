import os
import sqlite3
from datetime import timedelta

from flask import Flask, render_template, request, redirect, session, abort, flash, url_for
from dotenv import load_dotenv

from database import init_db
from schema import (
    authenticate_user,
    change_password,
    create_user,
    create_website,
    delete_website,
    get_user,
    get_user_websites,
    get_website_by_slug,
    update_user_profile,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-change-this-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "1") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

init_db()


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
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 80:
            return render_template("register.html", error="Username must be 3-80 characters."), 400
        if "@" not in email or len(email) > 255:
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
    return render_template(
        "dashboard.html",
        user=user,
        username=user.username,
        websites=websites,
    )


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
            if "@" not in email or len(email) > 255:
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


# Existing contact/newsletter storage is kept temporarily for compatibility.
def create_legacy_database():
    connection = sqlite3.connect("messages.db")
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    connection.commit()
    connection.close()


create_legacy_database()


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not email or not message:
        return "All fields are required.", 400
    connection = sqlite3.connect("messages.db")
    connection.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)", (name, email, message))
    connection.commit()
    connection.close()
    return "Message saved successfully!"


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("subscriber_email", "").strip()
    if not email:
        return "Email is required.", 400
    try:
        connection = sqlite3.connect("messages.db")
        connection.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
        connection.commit()
        connection.close()
        return "Subscribed successfully!"
    except sqlite3.IntegrityError:
        return "This email is already subscribed!", 409


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username", "") == os.getenv("ADMIN_USERNAME") and request.form.get("password", "") == os.getenv("ADMIN_PASSWORD"):
            session["admin_logged_in"] = True
            return redirect("/admin")
        return "Invalid username or password.", 401
    return render_template("login.html")


@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/login")
    connection = sqlite3.connect("messages.db")
    connection.row_factory = sqlite3.Row
    messages = connection.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    connection.close()
    return render_template("admin.html", messages=messages)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
