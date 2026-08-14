import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, abort
from dotenv import load_dotenv

from database import init_db
from schema import authenticate_user, create_user, create_website, get_user_websites, get_website_by_slug

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-change-this-secret")
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
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not username or not email or len(password) < 8:
            return render_template("register.html", error="Username, email and an 8+ character password are required."), 400
        user = create_user(username, email, password)
        if user is None:
            return render_template("register.html", error="Username or email is already in use."), 409
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect("/dashboard")
    return render_template("register.html")


@app.route("/user-login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        user = authenticate_user(request.form.get("username", "").strip(), request.form.get("password", ""))
        if user is None:
            return render_template("user_login.html", error="Invalid username or password."), 401
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect("/dashboard")
    return render_template("user_login.html")


@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/user-login")
    return render_template("dashboard.html", username=session.get("username", "User"), websites=get_user_websites(user_id))


@app.route("/dashboard/websites", methods=["POST"])
def create_website_route():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/user-login")
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    title = request.form.get("title", "My Website").strip()
    content = request.form.get("content", "").strip()
    if not name or not slug or not title:
        return render_template("dashboard.html", username=session.get("username", "User"), websites=get_user_websites(user_id), error="Name, slug and title are required."), 400
    if not all(c.isalnum() or c == "-" for c in slug) or slug.startswith("-") or slug.endswith("-"):
        return render_template("dashboard.html", username=session.get("username", "User"), websites=get_user_websites(user_id), error="Slug may contain only letters, numbers and hyphens."), 400
    website = create_website(user_id, name, slug, title, content)
    if website is None:
        return render_template("dashboard.html", username=session.get("username", "User"), websites=get_user_websites(user_id), error="That slug is already taken."), 409
    return redirect("/dashboard")


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
    return redirect("/user-login")


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
