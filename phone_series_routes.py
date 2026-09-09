"""Crawlable phone-series SEO hubs built from the published phone catalog."""

import re
from flask import Blueprint, abort, render_template
from sqlalchemy import text

from database import SessionLocal

phone_series_bp = Blueprint("phone_series", __name__)

# Curated families are intentionally limited to recognizable product lines. A page is
# only published when the catalog contains matching published models, preventing empty
# SEO pages and avoiding a large set of near-duplicate programmatic URLs.
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
    "nothing": {
        "phone-series": ("Nothing Phone Series", ["Nothing Phone"]),
    },
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


def _series_row(brand_slug, series_slug):
    definition = SERIES.get(brand_slug, {}).get(series_slug)
    if not definition:
        return None
    name, patterns = definition
    brand_name = BRAND_NAMES[brand_slug]
    clauses = ["LOWER(model) LIKE :p%d" % i for i in range(len(patterns))]
    params = {"brand": brand_name.lower()}
    params.update({f"p{i}": f"%{pattern.lower()}%" for i, pattern in enumerate(patterns)})
    with SessionLocal() as db:
        rows = db.execute(text(f"""SELECT id,brand,model,slug,short_description,image_url,release_date,price_usd,price_bdt,specs_json,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence
            FROM phone_catalog WHERE status='published' AND LOWER(brand)=:brand AND ({' OR '.join(clauses)})
            ORDER BY published_at DESC NULLS LAST, id DESC LIMIT 60"""), params).mappings().all()
    return {"name": name, "brand": brand_name, "slug": series_slug, "phones": [dict(r) for r in rows]} if rows else None


def available_series():
    result = []
    for brand_slug, series_map in SERIES.items():
        for series_slug, (name, _) in series_map.items():
            row = _series_row(brand_slug, series_slug)
            if row:
                result.append((brand_slug, series_slug, row))
    return result


@phone_series_bp.get("/phones/<brand>/series/<series_slug>")
def phone_series(brand, series_slug):
    brand_slug = _slug(brand)
    series_slug = _slug(series_slug)
    row = _series_row(brand_slug, series_slug)
    if not row:
        abort(404)
    phones = row["phones"]
    return render_template("phone_series.html", series=row, phones=phones)


def register_phone_series_routes(app):
    app.register_blueprint(phone_series_bp)
