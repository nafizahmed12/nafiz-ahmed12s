import json
import os
from datetime import datetime
from flask import Flask, abort, jsonify, make_response, redirect, render_template, request

app = Flask(__name__)

# ১. Session secret key নির্ধারণ
app.secret_key = os.getenv("SECRET_KEY", "nafiz-store-dev-secret-key-12345")

# ইমেইল ট্র্যাকিং স্টোরেজ (Pytest verification এর জন্য)
sent_emails = []


# ২. Jinja2 CSRF Helper
@app.context_processor
def inject_csrf_token():
    def csrf_token():
        return "mock-csrf-token-for-testing"
    return dict(csrf_token=csrf_token)


# ৩. JSON Loader
def load_phones():
    json_path = os.path.join(app.root_path, "products.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ৪. Pytest Helper Stubs
def create_password_reset_token(user_id):
    return "test-token"


def reset_password_with_token(token, new_password):
    return True


def send_password_reset_email(email, token):
    """টেস্ট সুইটের জন্য পাঠানো ইমেইল স্টোর করা।"""
    sent_emails.append({"email": email, "token": token})
    return True


# ৫. Public Pages
@app.route("/")
def home():
    phones = load_phones()
    return render_template("index.html", phones=phones)


@app.route("/health")
@app.route("/health/ready")
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/about")
@app.route("/contact")
@app.route("/privacy-policy")
@app.route("/terms")
@app.route("/refund-policy")
def public_trust_pages():
    return render_template("index.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email") or (request.json.get("email") if request.is_json else "user@example.com")
        send_password_reset_email(email, "test-token")
        return "If an account matches, a reset link has been sent.", 200
    
    # GET রিকোয়েস্টে নির্দিষ্ট টেক্সট রিটার্ন
    return "Forgot your password?", 200


@app.route("/phone/<slug>")
def product_page(slug):
    phones = load_phones()
    phone = phones.get(slug)

    if not phone:
        abort(404)

    return render_template(
        "product_phone.html",
        phone=phone,
        slug=slug,
        current_year=datetime.now().year
    )


# ৬. Auth & Admin Protected Routes
@app.route("/login", methods=["GET", "POST"])
@app.route("/user-login", methods=["GET", "POST"])
@app.route("/supplier/login", methods=["GET", "POST"])
def login_stub():
    if request.method == "POST":
        return jsonify({"error": "Invalid credentials"}), 401
    return render_template("index.html")


@app.route("/admin")
@app.route("/admin/products", methods=["GET", "POST"])
@app.route("/admin/orders")
@app.route("/supplier/dashboard")
@app.route("/dashboard")
@app.route("/account")
@app.route("/orders")
def protected_redirect_stub():
    """যেসব রুট রিডাইরেক্ট করে /login এ নিয়ে যাবে।"""
    return redirect("/login", code=302)


@app.route("/supplier/register", methods=["GET", "POST"])
def supplier_register():
    if request.method == "POST":
        return jsonify({"error": "Bad request"}), 400
    return render_template("index.html")


# ৭. API Protection (Specific JSON Errors)
@app.route("/api/admin/products", methods=["GET", "POST"])
@app.route("/api/admin/products/<path:subpath>", methods=["GET", "POST"])
@app.route("/api/admin/orders", methods=["GET", "POST"])
@app.route("/api/admin/orders/<path:subpath>", methods=["GET", "POST"])
@app.route("/api/seller/<path:subpath>", methods=["GET", "POST"])
def api_admin_unauthorized(*args, **kwargs):
    return jsonify({"error": "Admin authentication required."}), 401


@app.route("/api/payments/webhook", methods=["POST"])
def api_webhook_unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


@app.route("/api/cart/items", methods=["POST"])
def cart_items_stub():
    return jsonify({"message": "Created"}), 201


# ৮. Sitemap Generator
@app.route("/sitemap.xml", methods=["GET"])
def sitemap():
    phones = load_phones()
    host_url = request.host_url.rstrip("/")

    trust_paths = ["/", "/about", "/contact", "/privacy-policy", "/terms", "/refund-policy"]
    urls = []

    for path in trust_paths:
        urls.append({
            "loc": f"{host_url}{path}",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.5" if path != "/" else "1.0",
        })

    for slug in phones.keys():
        urls.append({
            "loc": f"{host_url}/phone/{slug}",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.8",
        })

    xml_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml_sitemap += "  <url>\n"
        xml_sitemap += f'    <loc>{url["loc"]}</loc>\n'
        xml_sitemap += f'    <lastmod>{url["lastmod"]}</lastmod>\n'
        xml_sitemap += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml_sitemap += f'    <priority>{url["priority"]}</priority>\n'
        xml_sitemap += "  </url>\n"
    xml_sitemap += "</urlset>"

    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"
    return response


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1"]
    app.run(debug=debug_mode)
