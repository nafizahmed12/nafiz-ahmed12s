"""Proxy verified Apple product media for first-party storefront imagery."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, Response


apple_media_bp = Blueprint("apple_media", __name__)
APPLE_PRODUCT_PAGE = "https://www.apple.com/iphone-18-pro/"


@apple_media_bp.get("/media/iphone-18-pro-max")
def iphone_18_pro_max_image():
    """Return Apple's current product-page social image without guessing a CDN URL."""
    try:
        request = Request(
            APPLE_PRODUCT_PAGE,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NafizStore/1.0)"},
        )
        with urlopen(request, timeout=8) as response:
            html = response.read(2_000_000).decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError):
        return Response(status=502)

    marker = '<meta property="og:image" content="'
    start = html.find(marker)
    if start == -1:
        return Response(status=502)
    start += len(marker)
    end = html.find('"', start)
    if end == -1:
        return Response(status=502)

    image_url = html[start:end].replace("&amp;", "&")
    if not image_url.startswith("https://www.apple.com/") and not image_url.startswith("https://images.apple.com/"):
        return Response(status=502)

    try:
        image_request = Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NafizStore/1.0)"},
        )
        with urlopen(image_request, timeout=8) as image_response:
            body = image_response.read(8_000_000)
            content_type = image_response.headers.get("Content-Type", "image/jpeg")
    except (HTTPError, URLError, TimeoutError):
        return Response(status=502)

    if not content_type.startswith("image/"):
        content_type = "image/jpeg"
    return Response(
        body,
        content_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


def register_apple_media_routes(app):
    if apple_media_bp.name not in app.blueprints:
        app.register_blueprint(apple_media_bp)
