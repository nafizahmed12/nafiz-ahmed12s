"""Production WSGI entrypoint with public AdSense infrastructure routes."""

from flask import Response, request

from app import app, products
from blog_routes import register_blog_routes
from phone_catalog_routes import register_phone_catalog_routes
from phone_compare_routes import register_phone_compare_routes
from phone_guides_routes import register_phone_guide_routes
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


register_blog_routes(app)
register_phone_catalog_routes(app)
register_phone_compare_routes(app)
register_phone_guide_routes(app)
register_best_phone_routes(app)
register_canonical_sitemap(app, products)


@app.get("/ads.txt")
def ads_txt():
    """Serve ads.txt from the root domain with a crawler-friendly 200 response."""
    response = Response(ADS_TXT, status=200, mimetype="text/plain")
    response.headers["Cache-Control"] = "public, max-age=3600"
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
