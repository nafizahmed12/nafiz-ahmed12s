"""Canonical, production-safe XML sitemap for Nafiz Ecommerce."""

import json
import os
from html import escape
from pathlib import Path

from flask import Response, request
from sqlalchemy import text

from database import SessionLocal
from phone_series_routes import available_series

PUBLIC_PATHS = (
    ("/", "weekly", "1.0"), ("/shop", "daily", "0.9"),
    ("/about", "monthly", "0.7"), ("/contact", "monthly", "0.7"),
    ("/privacy-policy", "yearly", "0.5"), ("/terms", "yearly", "0.5"),
    ("/refund-policy", "yearly", "0.5"), ("/disclaimer", "yearly", "0.5"),
    ("/phones", "daily", "0.9"), ("/phone-brands", "weekly", "0.9"),
    ("/compare", "daily", "0.9"), ("/phone-guides", "weekly", "0.9"),
    ("/best-phones", "weekly", "0.9"),
    ("/best-phones/best-gaming-phones", "weekly", "0.8"),
    ("/best-phones/best-camera-phones", "weekly", "0.8"),
    ("/best-phones/best-battery-phones", "weekly", "0.8"),
    ("/best-phones/best-5g-phones", "weekly", "0.8"),
    ("/best-phones/best-phones-under-20000", "weekly", "0.8"),
    ("/best-phones/best-phones-under-30000", "weekly", "0.8"),
    ("/best-phones/best-flagship-phones", "weekly", "0.8"),
    ("/iphone-18", "weekly", "0.9"), ("/iphone-18-pro", "weekly", "0.9"),
    ("/iphone-18-pro-max", "weekly", "0.9"), ("/iphone-18-series", "weekly", "0.9"),
    ("/iphone-18-comparison", "weekly", "0.8"),
)


def _base_url():
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    return configured or request.url_root.rstrip("/")


def _registry_paths(base_url):
    path = Path(__file__).resolve().parent / "seo" / "registry.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    paths = []
    for page in data.get("pages", []):
        canonical = str(page.get("canonical", "")).strip()
        if not canonical.startswith(base_url + "/") or page.get("route_kind") == "dynamic":
            continue
        route = canonical[len(base_url):] or "/"
        if "?" not in route:
            paths.append(route)
    return paths


def _published_article_slugs():
    try:
        with SessionLocal() as db:
            return db.execute(text("""SELECT slug FROM blog_articles
                WHERE status='published' AND published_at IS NOT NULL
                ORDER BY published_at DESC, id DESC""")).scalars().all()
    except Exception:
        return []


def _published_catalog_rows():
    try:
        with SessionLocal() as db:
            return db.execute(text("""SELECT brand,slug FROM phone_catalog
                WHERE status='published' ORDER BY brand, id DESC""")).mappings().all()
    except Exception:
        return []


def _available_series():
    """Optional series data must never make /sitemap.xml return 500."""
    try:
        return available_series()
    except Exception:
        return []


def _brand_slug(brand):
    return "-".join(str(brand).lower().split())


def register_canonical_sitemap(app, products):
    def canonical_sitemap():
        base_url = _base_url()
        candidates = list(PUBLIC_PATHS)
        known = {path for path, _, _ in candidates}

        for path in _registry_paths(base_url):
            if path not in known:
                candidates.append((path, "weekly", "0.8")); known.add(path)

        for slug in sorted(products):
            path = f"/phone-detail/{slug}"
            if path not in known:
                candidates.append((path, "daily", "0.8")); known.add(path)

        for row in _published_catalog_rows():
            brand = str(row.get("brand") or "").strip()
            slug = str(row.get("slug") or "").strip()
            if not brand or not slug:
                continue
            brand_path = f"/phones/{_brand_slug(brand)}"
            product_path = f"/phones/{_brand_slug(brand)}/{slug}"
            if brand_path not in known:
                candidates.append((brand_path, "weekly", "0.8")); known.add(brand_path)
            if product_path not in known:
                candidates.append((product_path, "weekly", "0.8")); known.add(product_path)

        for brand_slug, series_slug, _ in _available_series():
            path = f"/phones/{brand_slug}/series/{series_slug}"
            if path not in known:
                candidates.append((path, "weekly", "0.8")); known.add(path)

        for slug in _published_article_slugs():
            path = f"/blog/{slug}"
            if path not in known:
                candidates.append((path, "weekly", "0.8")); known.add(path)

        for path in (
            "/phone-guides/how-to-choose-a-smartphone", "/phone-guides/best-phone-for-gaming",
            "/phone-guides/best-phone-camera-guide", "/phone-guides/best-phone-battery-guide",
            "/phone-guides/phone-display-buying-guide", "/phone-guides/phone-storage-ram-guide",
            "/phone-guides/phone-5g-network-guide", "/phone-guides/flagship-vs-midrange-phone",
        ):
            if path not in known:
                candidates.append((path, "monthly", "0.8")); known.add(path)

        entries = []
        for path, changefreq, priority in candidates:
            loc = escape(base_url + (path if path.startswith("/") else "/" + path), quote=True)
            entries.append(
                f"  <url><loc>{loc}</loc><changefreq>{changefreq}</changefreq>"
                f"<priority>{priority}</priority></url>"
            )
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entries) + '\n</urlset>\n'
        )
        response = Response(content, status=200, mimetype="application/xml")
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    app.view_functions["sitemap_xml"] = canonical_sitemap
