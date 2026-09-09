"""Curated, crawlable smartphone recommendation pages built from the published phone catalog."""
from flask import Blueprint, abort, render_template
from sqlalchemy import text
from database import SessionLocal

best_phones_bp = Blueprint("best_phones", __name__)

CATEGORIES = {
    "best-phones": {
        "title": "Best Phones in 2026: Top Smartphones by Budget & Need",
        "description": "Explore the best smartphones in 2026 by performance, cameras, battery, gaming and overall value using published phone specifications.",
        "heading": "Best Phones in 2026",
        "intro": "Choosing a phone depends on budget, performance, camera quality, battery life and software support. This guide groups published models from our catalog by practical buying intent so you can compare the specifications before making a decision.",
        "terms": (),
    },
    "best-gaming-phones": {
        "title": "Best Gaming Phones in 2026: Performance & Display Picks",
        "description": "Find strong gaming phone options in 2026 by chipset, display, RAM, battery and cooling-oriented specifications.",
        "heading": "Best Gaming Phones",
        "intro": "Gaming phones need sustained performance, a fast and responsive display, enough memory and a battery that can handle longer sessions. These recommendations prioritize published performance and gaming-relevant specifications.",
        "terms": ("gaming", "snapdragon", "a19", "a19 pro", "tensor", "dimensity", "120hz", "144hz"),
    },
    "best-camera-phones": {
        "title": "Best Camera Phones in 2026: Top Picks for Photography",
        "description": "Compare camera-focused smartphones in 2026 using published camera hardware, stabilization, telephoto and video specifications.",
        "heading": "Best Camera Phones",
        "intro": "Camera quality is more than megapixels. Sensor hardware, stabilization, telephoto capability, video features and image processing all matter. Use these catalog picks as a starting point and open each model for the detailed specifications.",
        "terms": ("camera", "48mp", "50mp", "64mp", "108mp", "200mp", "telephoto", "ois", "periscope"),
    },
    "best-battery-phones": {
        "title": "Best Battery Phones in 2026: Long-Lasting Smartphone Picks",
        "description": "Explore smartphones with battery and charging specifications suited to long daily use, travel and heavy workloads.",
        "heading": "Best Battery Phones",
        "intro": "Battery endurance depends on capacity, display efficiency, chipset and software—not capacity alone. These pages highlight models whose published specifications make them useful candidates for long battery life.",
        "terms": ("battery", "5000mah", "5200mah", "5500mah", "6000mah", "6500mah", "7000mah", "charging"),
    },
    "best-5g-phones": {
        "title": "Best 5G Phones in 2026: Smartphones with 5G Support",
        "description": "Browse 5G-capable smartphones and compare their processors, network support, displays, cameras and battery specifications.",
        "heading": "Best 5G Phones",
        "intro": "5G support is useful only when the exact regional model supports the bands used by your carrier. These models are cataloged as 5G-capable, but buyers should verify the exact model number and local network compatibility.",
        "terms": ("5g",),
    },
    "best-phones-under-20000": {
        "title": "Best Phones Under ৳20,000 in Bangladesh: What to Look For",
        "description": "Compare phone options around the ৳20,000 budget with practical specifications for everyday use, cameras, battery and performance.",
        "heading": "Best Phones Under ৳20,000",
        "intro": "Prices change by seller, region and promotion, so this page focuses on models that fit the budget when reliable Bangladesh price data is available. Always check the current local price and exact configuration before buying.",
        "terms": (), "max_price": 20000,
    },
    "best-phones-under-30000": {
        "title": "Best Phones Under ৳30,000 in Bangladesh: Top Picks",
        "description": "Explore smartphone options around the ৳30,000 budget and compare display, chipset, cameras, battery and storage.",
        "heading": "Best Phones Under ৳30,000",
        "intro": "The ৳30,000 segment often balances display quality, performance and camera hardware. Use the published catalog details to shortlist models, then verify the current Bangladesh price and regional configuration.",
        "terms": (), "max_price": 30000,
    },
    "best-flagship-phones": {
        "title": "Best Flagship Phones in 2026: Premium Smartphone Picks",
        "description": "Compare flagship smartphones in 2026 from Apple, Samsung, Google and other major brands by performance, camera, display and features.",
        "heading": "Best Flagship Phones",
        "intro": "Flagship phones usually combine the newest processors, premium displays, advanced cameras and longer software support. These recommendations are based on the published models available in the catalog, not paid placement.",
        "terms": ("pro", "ultra", "plus", "fold", "flagship", "pixel 10", "galaxy s26", "iphone 17"),
    },
}


def _phone_rows(category):
    with SessionLocal() as db:
        rows = db.execute(text("""SELECT id,brand,model,slug,short_description,image_url,release_date,price_usd,price_bdt,specs_json,seo_description
            FROM phone_catalog WHERE status='published' ORDER BY published_at DESC NULLS LAST, id DESC LIMIT 250""")).mappings().all()
    max_price = category.get("max_price")
    terms = tuple(t.lower() for t in category.get("terms", ()))
    scored = []
    for row in rows:
        item = dict(row)
        haystack = " ".join(str(item.get(k) or "") for k in ("brand", "model", "short_description", "specs_json")).lower()
        if max_price is not None:
            raw = str(item.get("price_bdt") or "").replace(",", "").replace("৳", "").strip()
            try:
                price = float(raw)
            except ValueError:
                continue
            if price > max_price:
                continue
        score = sum(1 for term in terms if term in haystack)
        if terms and score == 0:
            continue
        score += 1 if item.get("brand") in {"Apple", "Samsung", "Google", "OnePlus", "Xiaomi"} else 0
        scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("model") or "")))
    return [item for _, item in scored[:18]]


@best_phones_bp.get("/best-phones")
def best_phones_index():
    return _render("best-phones")


@best_phones_bp.get("/best-phones/<category>")
def best_phones_category(category):
    if category not in CATEGORIES:
        abort(404)
    return _render(category)


def _render(category_key):
    category = CATEGORIES[category_key]
    phones = _phone_rows(category)
    return render_template("best_phones.html", category_key=category_key, category=category, phones=phones, categories=CATEGORIES)


def register_best_phone_routes(app):
    app.register_blueprint(best_phones_bp)
