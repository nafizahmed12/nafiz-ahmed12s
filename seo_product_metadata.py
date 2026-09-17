"""Isolated canonical/social metadata normalization for public phone detail pages."""

import os
import re
from html import escape
from urllib.parse import urlsplit

from flask import request


def _public_base_url():
    return os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")


def _canonical_url():
    base = _public_base_url()
    path = urlsplit(request.url).path or "/"
    path = path.rstrip("/") or "/"
    return f"{base}{path}"


def _replace_or_add_tag(body, pattern, replacement):
    updated, count = re.subn(pattern, replacement, body, count=1, flags=re.IGNORECASE)
    return updated if count else body.replace("</head>", replacement + "</head>", 1)


def normalize_product_metadata(response):
    """Normalize existing phone-page SEO tags without changing routes or page content."""
    if request.method != "GET" or response.status_code != 200 or "text/html" not in response.content_type:
        return response
    if not request.path.startswith("/phone-detail/"):
        return response

    response.direct_passthrough = False
    body = response.get_data(as_text=True)
    if "</head>" not in body:
        return response

    canonical = escape(_canonical_url(), quote=True)
    body = _replace_or_add_tag(
        body,
        r'<link\s+rel=["\']canonical["\'][^>]*>',
        f'<link rel="canonical" href="{canonical}">',
    )
    body = _replace_or_add_tag(
        body,
        r'<meta\s+property=["\']og:url["\'][^>]*>',
        f'<meta property="og:url" content="{canonical}">',
    )

    head_end = body.lower().find("</head>")
    head = body[:head_end]
    tail = body[head_end:]
    head = head.replace("Nafiz Store", "Nafiz Ecommerce")
    body = head + tail

    response.set_data(body)
    return response


def register_product_metadata(app):
    app.after_request(normalize_product_metadata)
