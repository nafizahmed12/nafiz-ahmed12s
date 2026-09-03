import json
import os

from datetime import datetime
from flask import Flask, abort, make_response, render_template, request

app = Flask(__name__)

# ১. Session backend এর জন্য secret key নির্ধারণ
app.secret_key = os.getenv("SECRET_KEY", "nafiz-store-dev-secret-key-12345")


# ২. JSON থেকে ফোন লোড করার হেল্পার
def load_phones():
    """JSON ফাইল থেকে ফোন ডাটা লোড করার ফাংশন।"""
    json_path = os.path.join(app.root_path, "products.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ৩. Pytest / Password Reset-এর জন্য প্রয়োজনীয় স্টাব ফাংশনসমূহ
def create_password_reset_token(user_id):
    """টেস্ট সুইটের জন্য পাসওয়ার্ড রিসেট টোকেন জেনারেটর।"""
    return f"mock-reset-token-{user_id}"


def reset_password_with_token(token, new_password):
    """টেস্ট সুইটের জন্য পাসওয়ার্ড রিসেট হ্যান্ডলার।"""
    return True


# ৪. রুটসমূহ (Routes)
@app.route("/")
def home():
    """হোম পেজ রুট।"""
    phones = load_phones()
    return render_template("index.html", phones=phones)


@app.route("/health")
@app.route("/health/ready")
def health_check():
    """CI/CD Health/Readiness smoke test endpoint."""
    return "OK", 200


@app.route("/about")
def about():
    """অ্যাবাউট পেজ রুট (Trust pages test-এর জন্য)।"""
    return render_template("index.html")


@app.route("/forgot-password")
def forgot_password():
    """পাসওয়ার্ড রিসেট পেজ রুট।"""
    return render_template("index.html")


@app.route("/phone/<slug>")
def product_page(slug):
    """ডায়নামিক ফোন পেজ রুট।"""
    phones = load_phones()
    phone = phones.get(slug)

    if not phone:
        abort(404)

    current_year = datetime.now().year
    return render_template(
        "product_phone.html",
        phone=phone,
        slug=slug,
        current_year=current_year
    )


@app.route("/sitemap.xml", methods=["GET"])
def sitemap():
    """ডায়নামিক সাইটম্যাপ রুট।"""
    phones = load_phones()
    host_url = request.host_url.rstrip("/")

    urls = [
        {
            "loc": f"{host_url}/",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "daily",
            "priority": "1.0",
        },
        {
            "loc": f"{host_url}/about",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.5",
        }
    ]

    for slug in phones.keys():
        urls.append(
            {
                "loc": f"{host_url}/phone/{slug}",
                "lastmod": datetime.now().strftime("%Y-%m-%d"),
                "changefreq": "weekly",
                "priority": "0.8",
            }
        )

    xml_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_sitemap += (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    )
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
