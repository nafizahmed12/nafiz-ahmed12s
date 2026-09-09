"""Canonical sitemap implementation for the production Flask application."""

import json
import os
from html import escape
from pathlib import Path

from flask import Response, request
from sqlalchemy import text

from database import SessionLocal


PUBLIC_PATHS = (
    ("/", "weekly", "1.0"),
    ("/shop", "daily", "0.9"),
    ("/about", "monthly", "0.7"),
    ("/contact", "monthly", "0.7"),
    ("/privacy-policy", "yearly", "0.5"),
    ("/terms", "yearly", "0.5"),
    ("/refund-policy", "yearly", "0.5"),
    ("/phones", "daily", "0.9"),
    ("/iphone-18", "weekly", "0.9"),
    ("/iphone-18-pro", "weekly", "0.9"),
    ("/iphone-18-pro-max", "weekly", "0.9"),
    ("/iphone-18-series", "weekly", "0.9"),
    ("/iphone-18-comparison", "weekly", "0.8"),
)


def _base_url():
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return request.url_root.rstrip("/")


def _registry_paths(base_url):
    registry_path = Path(__file__).resolve().parent / "seo" / "registry.json"
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    paths = []
    for page in data.get("pages", []):
        canonical = str(page.get("canonical", "")).strip()
        route_kind = page.get("route_kind")
        if not canonical.startswith(base_url + "/") or route_kind == "dynamic":
            continue
        path = canonical[len(base_url):] or "/"
        if "?" not in path:
            paths.append(path)
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


def _brand_slug(brand):
    return "-".join(str(brand).lower().split())


def register_canonical_sitemap(app, products):
    """Replace the legacy sitemap view with a canonical, indexable URL set."""

    def canonical_sitemap():
        base_url = _base_url()
        candidates = list(PUBLIC_PATHS)
        known = {path for path, _, _ in candidates}
        for path in _registry_paths(base_url):
            if path not in known:
                candidates.append((path, "weekly", "0.8"))
                known.add(path)

        for slug in sorted(products):
            path = f"/phone-detail/{slug}"
            if path not in known:
                candidates.append((path, "daily", "0.8"))
                known.add(path)

        brands = set()
        for row in _published_catalog_rows():
            brand = row["brand"]
            brands.add(brand)
            path = f"/phones/{_brand_slug(brand)}"
            if path not in known:
                candidates.append((path, "weekly", "0.8"))
                known.add(path)
            path = f"/phones/{_brand_slug(brand)}/{row['slug']}"
            if path not in known:
                candidates.append((path, "weekly", "0.8"))
                known.add(path)

        for slug in _published_article_slugs():
            path = f"/blog/{slug}"
            if path not in known:
                candidates.append((path, "weekly", "0.8"))
                known.add(path)

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
            + "\n".join(entries)
            + '\n</urlset>\n'
        )
        response = Response(content, status=200, mimetype="application/xml")
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    app.view_functions["sitemap_xml"] = canonical_sitemap
