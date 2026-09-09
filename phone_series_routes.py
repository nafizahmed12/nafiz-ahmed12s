"""Crawlable phone-series SEO hubs built from the published phone catalog."""

import re
from flask import Blueprint, abort, render_template
from sqlalchemy import text

from database import SessionLocal

phone_series_bp = Blueprint("phone_series", __name__)

SERIES = {
    "apple": {
        "iphone-18-series": ("Apple iPhone 18 Series", ["iPhone 18"]),
        "iphone-17-series": ("Apple iPhone 17 Series", ["iPhone 17"]),
        "iphone-16-series": ("Apple iPhone 16 Series", ["iPhone 16"]),
        "iphone-15-series": ("Apple iPhone 15 Series", ["iPhone 15"]),
    },
    "samsung": {
        "galaxy-s-series": ("Samsung Galaxy S Series", ["Galaxy S"]),
        "galaxy-a-series": ("Samsung Galaxy A Series", ["Galaxy A"]),
        "galaxy-z-series": ("Samsung Galaxy Z Foldable Series", ["Galaxy Z"]),
        "galaxy-note-series": ("Samsung Galaxy Note Series", ["Galaxy Note"]),
    },
    "google": {
        "pixel-series": ("Google Pixel Series", ["Pixel "]),
        "pixel-a-series": ("Google Pixel A Series", ["Pixel 8a", "Pixel 7a", "Pixel 6a"]),
        "pixel-pro-series": ("Google Pixel Pro Series", ["Pixel 8 Pro", "Pixel 7 Pro", "Pixel 6 Pro"]),
    },
    "oneplus": {
        "oneplus-number-series": ("OnePlus Number Series", ["OnePlus 11", "OnePlus 12", "OnePlus 13", "OnePlus 10"]),
        "oneplus-nord-series": ("OnePlus Nord Series", ["OnePlus Nord"]),
    },
    "xiaomi": {
        "xiaomi-number-series": ("Xiaomi Number Series", ["Xiaomi 14", "Xiaomi 15", "Xiaomi 13", "Xiaomi 12"]),
        "xiaomi-t-series": ("Xiaomi T Series", ["Xiaomi 14T", "Xiaomi 14T Pro", "Xiaomi 13T", "Xiaomi 13T Pro"]),
    },
    "redmi": {
        "redmi-note-series": ("Redmi Note Series", ["Redmi Note"]),
        "redmi-number-series": ("Redmi Number Series", ["Redmi "]),
    },
    "poco": {
        "poco-f-series": ("POCO F Series", ["POCO F"]),
        "poco-x-series": ("POCO X Series", ["POCO X"]),
        "poco-m-series": ("POCO M Series", ["POCO M"]),
    },
    "oppo": {
        "find-series": ("OPPO Find Series", ["Find X", "Find N"]),
        "reno-series": ("OPPO Reno Series", ["Reno"]),
    },
    "vivo": {
        "x-series": ("vivo X Series", ["X100", "X200", "X90", "X80"]),
        "v-series": ("vivo V Series", ["V30", "V40", "V50", "V29"]),
    },
    "realme": {
        "gt-series": ("realme GT Series", ["GT"]),
        "number-series": ("realme Number Series", ["realme 12", "realme 13", "realme 14", "realme 11"]),
    },
    "motorola": {
        "edge-series": ("Motorola Edge Series", ["Edge"]),
        "moto-g-series": ("Motorola Moto G Series", ["Moto G"]),
        "razr-series": ("Motorola Razr Series", ["Razr"]),
    },
    "honor": {
        "magic-series": ("HONOR Magic Series", ["Magic"]),
        "x-series": ("HONOR X Series", ["HONOR X", "Honor X"]),
    },
    "nothing": {"phone-series": ("Nothing Phone Series", ["Nothing Phone"])},
    "asus": {
        "rog-phone-series": ("ASUS ROG Phone Series", ["ROG Phone"]),
        "zenfone-series": ("ASUS Zenfone Series", ["Zenfone"]),
    },
    "sony": {
        "xperia-1-series": ("Sony Xperia 1 Series", ["Xperia 1"]),
        "xperia-5-series": ("Sony Xperia 5 Series", ["Xperia 5"]),
    },
}

BRAND_NAMES = {
    "apple": "Apple", "samsung": "Samsung", "google": "Google", "oneplus": "OnePlus",
    "xiaomi": "Xiaomi", "redmi": "Redmi", "poco": "POCO", "oppo": "OPPO", "vivo": "vivo",
    "realme": "realme", "motorola": "Motorola", "honor": "HONOR", "nothing": "Nothing",
    "asus": "ASUS", "sony": "Sony",
}


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")[:180]


def _matches(model, patterns):
    model = (model or "").lower()
    return any(pattern.lower() in model for pattern in patterns)


def _build_series(rows, brand_slug, series_slug):
    definition = SERIES.get(brand_slug, {}).get(series_slug)
    if not definition:
        return None
    name, patterns = definition
    brand_name = BRAND_NAMES[brand_slug]
    phones = [dict(row) for row in rows if _matches(row["model"], patterns)]
    if not phones:
        return None
    return {"name": name, "brand": brand_name, "slug": series_slug, "phones": phones[:60]}


def available_series(brand_slug=None):
    """Return only series backed by published catalog rows.

    A single catalog query is used for sitemap generation and brand pages, avoiding
    one database query per candidate series.
    """
    requested = _slug(brand_slug) if brand_slug else None
    brands = [requested] if requested else list(SERIES)
    brands = [brand for brand in brands if brand in SERIES]
    if not brands:
        return []
    brand_names = [BRAND_NAMES[brand].lower() for brand in brands]
    params = {f"brand{i}": value for i, value in enumerate(brand_names)}
    brand_clause = ", ".join(f":brand{i}" for i in range(len(brand_names)))
    with SessionLocal() as db:
        rows = db.execute(text(f"""SELECT id,brand,model,slug,short_description,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence
            FROM phone_catalog
            WHERE status='published' AND LOWER(brand) IN ({brand_clause})
            ORDER BY published_at DESC NULLS LAST, id DESC"""), params).mappings().all()
    grouped = {brand: [] for brand in brands}
    for row in rows:
        grouped.setdefault(_slug(row["brand"]), []).append(row)
    result = []
    for brand in brands:
        for series_slug in SERIES[brand]:
            row = _build_series(grouped.get(brand, []), brand, series_slug)
            if row:
                result.append((brand, series_slug, row))
    return result


@phone_series_bp.get("/phone-brands")
def phone_brands_index():
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT LOWER(brand) AS brand_key, MIN(brand) AS brand_name, COUNT(*) AS phone_count
            FROM phone_catalog WHERE status='published' GROUP BY LOWER(brand) ORDER BY MIN(brand)""")).mappings().all()
    available = {(brand, slug): row["name"] for brand, slug, row in available_series()}
    brands = []
    for row in rows:
        key = _slug(row["brand_name"])
        brand_series = [(slug, name) for slug, (name, _) in SERIES.get(key, {}).items() if (key, slug) in available]
        brands.append({"slug": key, "name": row["brand_name"], "phone_count": row["phone_count"], "series": brand_series})
    return render_template("phone_brands.html", brands=brands)


@phone_series_bp.get("/phones/<brand>/series/<series_slug>")
def phone_series(brand, series_slug):
    brand_slug = _slug(brand)
    series_slug = _slug(series_slug)
    matches = [row for b, s, row in available_series(brand_slug) if s == series_slug]
    if not matches:
        abort(404)
    series = matches[0]
    return render_template("phone_series.html", series=series, phones=series["phones"])


def register_phone_series_routes(app):
    app.register_blueprint(phone_series_bp)
