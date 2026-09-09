"""Production WSGI entrypoint with public AdSense infrastructure routes."""

from flask import Response, request

from app import app


ADS_TXT = "google.com, pub-5012987374131521, DIRECT, f08c47fec0942fa0\n"
ADSENSE_META = '<meta name="google-adsense-account" content="ca-pub-5012987374131521">'


@app.get("/ads.txt")
def ads_txt():
    """Serve ads.txt from the root domain with a crawler-friendly 200 response."""
    response = Response(ADS_TXT, status=200, mimetype="text/plain")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.after_request
def add_adsense_site_verification(response):
    """Expose the AdSense account meta tag on public HTML pages without editing templates."""
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


application = app
