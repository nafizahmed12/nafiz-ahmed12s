"""Production WSGI entrypoint with public AdSense and SEO infrastructure routes."""

from html import escape
from urllib.parse import urlsplit
import json
import os
import re

from flask import Response, request

from app import app, products
from blog_routes import register_blog_routes
from phone_catalog_routes import register_phone_catalog_routes
from phone_compare_routes import register_phone_compare_routes
from phone_guides_routes import register_phone_guide_routes
from phone_series_routes import register_phone_series_routes
from best_phones_routes import register_best_phone_routes
from seo_sitemap import register_canonical_sitemap


ADS_TXT = "google.com, pub-5012987374131521, DIRECT, f08c47fec0942fa0\n"
ADSENSE_META = '<meta name="google-adsense-account" content="ca-pub-5012987374131521">'
ADSENSE_CSP = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
    "form-action 'self'; "
    "img-src 'self' data: https:; font-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline' https:; "
    "script-src 'self' 'unsafe-inline' https://pagead2.googlesyndication.com https://www.googletagmanager.com; "
    "connect-src 'self' https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net; "
    "frame-src 'self' https://googleads.g.doubleclick.net https://tpc.googlesyndication.com; "
    "media-src 'self' https:; worker-src 'self'; manifest-src 'self';"
)

SEO_META = {
    "/": ("Nafiz Ecommerce — Mobiles, Laptops & Electronics", "Shop mobiles, laptops, electronics, accessories and more at Nafiz Ecommerce. Discover products and deals with secure checkout and fast delivery."),
    "/shop": ("Shop Mobiles, Laptops & Electronics | Nafiz Ecommerce", "Browse mobiles, laptops, accessories and electronics at Nafiz Ecommerce. Find products, compare options and shop online."),
    "/phones": ("Mobile Phones — Specs, Prices & Comparisons | Nafiz Ecommerce", "Explore mobile phones, specifications, prices and comparisons. Find the right smartphone for your budget and needs."),
    "/phone-brands": ("Phone Brands — Compare Smartphones | Nafiz Ecommerce", "Explore popular smartphone brands and compare phones, specifications and prices in one place."),
    "/compare": ("Compare Mobile Phones — Specs & Prices | Nafiz Ecommerce", "Compare smartphone specifications, features and prices to choose the best phone for you."),
    "/phone-guides": ("Mobile Phone Buying Guides | Nafiz Ecommerce", "Practical smartphone buying guides covering gaming, cameras, battery, 5G, displays, storage and more."),
    "/best-phones": ("Best Phones — Top Smartphones by Budget & Use | Nafiz Ecommerce", "Find the best smartphones for gaming, cameras, battery life, 5G, flagship features and different budgets."),
    "/about": ("About Nafiz Ecommerce", "Learn more about Nafiz Ecommerce and our goal of making online shopping simple, useful and trustworthy."),
    "/contact": ("Contact Nafiz Ecommerce", "Contact Nafiz Ecommerce for questions, support and help with products or orders."),
}


def _canonical_url():
    base = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")
    path = urlsplit(request.url).path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return f"{base}{path}"


def _inject_phone_structured_seo(body, canonical):
    """Add a breadcrumb entity and safe social metadata to individual catalog phone pages."""
    if not request.path.startswith("/phones/"):
        return body
    parts = [part for part in request.path.split("/") if part]
    if len(parts) != 3:
        return body

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.IGNORECASE | re.DOTALL)
    model = re.sub(r"<[^>]+>", " ", h1_match.group(1)) if h1_match else parts[-1].replace("-", " ").title()
    model = " ".join(model.split())
    brand = parts[1].replace("-", " ").title()
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{request.url_root.rstrip('/')}/"},
            {"@type": "ListItem", "position": 2, "name": "Phones", "item": f"{request.url_root.rstrip('/')}/phones"},
            {"@type": "ListItem", "position": 3, "name": f"{brand} Phones", "item": f"{request.url_root.rstrip('/')}/phones/{parts[1]}"},
            {"@type": "ListItem", "position": 4, "name": model, "item": canonical},
        ],
    }
    additions = [f'<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">']
    if 'name="twitter:card"' not in body:
        additions.append('<meta name="twitter:card" content="summary_large_image">')
    if 'name="twitter:title"' not in body:
        additions.append(f'<meta name="twitter:title" content="{escape(model + " Specs, Price & Features | Nafiz Ecommerce", quote=True)}">')
    if 'name="twitter:description"' not in body:
        additions.append(f'<meta name="twitter:description" content="{escape(model + " specifications, price, release details and key features.", quote=True)}">')
    additions.append(f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}</script>')
    return body.replace("</head>", "".join(additions) + "</head>", 1)


def _inject_seo(response):
    """Add fallback canonical and social metadata without overriding page metadata."""
    if request.method != "GET" or response.status_code != 200 or "text/html" not in response.content_type:
        return response
    if request.path.startswith(("/admin", "/dashboard", "/account", "/user-login", "/register", "/login", "/orders")):
        return response

    response.direct_passthrough = False
    body = response.get_data(as_text=True)
    if "</head>" not in body:
        return response

    additions = []
    canonical = escape(_canonical_url(), quote=True)
    if 'rel="canonical"' not in body:
        additions.append(f'<link rel="canonical" href="{canonical}">')

    title, description = SEO_META.get(request.path, (None, None))
    if title and "<title" not in body.lower():
        additions.append(f"<title>{escape(title)}</title>")
    if description and 'name="description"' not in body.lower():
        additions.append(f'<meta name="description" content="{escape(description, quote=True)}">')

    og_title = title or "Nafiz Ecommerce"
    og_description = description or "Nafiz Ecommerce — mobiles, laptops, electronics and more."
    if 'property="og:title"' not in body:
        additions.append(f'<meta property="og:title" content="{escape(og_title, quote=True)}">')
    if 'property="og:description"' not in body:
        additions.append(f'<meta property="og:description" content="{escape(og_description, quote=True)}">')
    if 'property="og:url"' not in body:
        additions.append(f'<meta property="og:url" content="{canonical}">')
    if 'property="og:type"' not in body:
        additions.append('<meta property="og:type" content="website">')

    if additions:
        body = body.replace("</head>", "".join(additions) + "</head>", 1)
    body = _inject_phone_structured_seo(body, canonical)
    response.set_data(body)
    return response


register_blog_routes(app)
register_phone_catalog_routes(app)
register_phone_compare_routes(app)
register_phone_guide_routes(app)
register_phone_series_routes(app)
register_best_phone_routes(app)
register_canonical_sitemap(app, products)


@app.get("/ads.txt")
def ads_txt():
    """Serve ads.txt from the root domain with a crawler-friendly 200 response."""
    response = Response(ADS_TXT, status=200, mimetype="text/plain")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.after_request
def add_public_seo_metadata(response):
    """Add safe fallback canonical/Open Graph metadata to public HTML pages."""
    return _inject_seo(response)


@app.after_request
def add_noindex_to_private_routes(response):
    """Prevent private, transactional, and API endpoints from entering search indexes."""
    noindex_prefixes = (
        "/admin", "/dashboard", "/account", "/login", "/user-login", "/register",
        "/logout", "/user-logout", "/forgot-password", "/reset-password",
        "/admin-forgot-password", "/admin-reset-password", "/checkout", "/cart",
        "/orders", "/seller", "/supplier", "/api/",
    )
    if request.path == "/" or not request.path.startswith(noindex_prefixes):
        return response
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.after_request
def add_adsense_site_verification(response):
    """Expose the AdSense account meta tag on public HTML pages."""
    if (
        request.method == "GET"
        and response.status_code == 200
        and "text/html" in response.content_type
        and not request.path.startswith(("/admin", "/dashboard", "/account", "/user-login", "/register"))
    ):
        response.direct_passthrough = False
        body = response.get_data(as_text=True)
        if "google-adsense-account" not in body and "</head>" in body:
            response.set_data(body.replace("</head>", f"{ADSENSE_META}</head>", 1))
    return response


@app.after_request
def allow_adsense_crawlers(response):
    """Keep crawler endpoints explicit and make the CSP compatible with AdSense."""
    if request.path == "/robots.txt" and request.method == "GET" and response.status_code == 200:
        response.direct_passthrough = False
        body = response.get_data(as_text=True)
        if "Allow: /ads.txt" not in body:
            body = body.replace("Allow: /\n", "Allow: /\nAllow: /ads.txt\n", 1)
            response.set_data(body)
    if request.path != "/ads.txt":
        response.headers["Content-Security-Policy"] = ADSENSE_CSP
    return response


application = app
