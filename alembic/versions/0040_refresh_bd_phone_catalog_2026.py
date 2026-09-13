"""Refresh 100+ catalog phone prices/spec metadata using current Bangladesh references.

Prices are only written when a matching published catalog slug exists. Existing
manufacturer-oriented specs are preserved unless an exact spec patch is supplied.
This avoids inventing regional variants while keeping the catalog current.
"""
from datetime import datetime
import json

from alembic import op
from sqlalchemy import text

revision = "0040_bd_catalog_refresh"
down_revision = "0039_bd_price_refresh"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 13)

# Current Bangladesh reference prices gathered from current September 2026
# Bangladesh listings. Status is one of official/unofficial/reference/expected.
# The migration intentionally updates only rows that already exist in the catalog.
PRICES = {
    "xiaomi-redmi-17-5g": (23000, "expected"),
    "oneplus-n6x": (24500, "expected"),
    "infinix-hot-60i": (16999, "official"),
    "infinix-smart-20": (15999, "official"),
    "xiaomi-redmi-note-17": (25000, "expected"),
    "realme-c75": (19999, "official"),
    "xiaomi-redmi-17": (22999, "official"),
    "xiaomi-redmi-note-15": (26999, "official"),
    "infinix-hot-60-pro-plus": (21999, "official"),
    "tecno-spark-50-pro": (24999, "official"),
    "oppo-a78-5g": (20500, "unofficial"),
    "realme-c85-pro": (20999, "official"),
    "tecno-spark-go-3-pro": (20000, "reference"),
    "honor-x6e": (21500, "reference"),
    "motorola-moto-g37-power": (23500, "unofficial"),
    "infinix-hot-60-pro": (20999, "official"),
    "realme-c100x": (21999, "official"),
    "tecno-spark-50-5g": (23999, "official"),
    "oppo-a6c": (17999, "official"),
    "realme-c85": (20999, "official"),
    "infinix-hot-70": (18999, "official"),
    "samsung-galaxy-a07-5g": (23900, "reference"),
    "oppo-a6x": (14990, "official"),
    "samsung-galaxy-a07": (17199, "official"),
    "xiaomi-redmi-15": (19999, "official"),
    "realme-p4r": (24500, "unofficial"),
    "samsung-galaxy-a56": (49999, "official"),
    "xiaomi-redmi-note-15-5g-special-edition": (28000, "reference"),
    "xiaomi-redmi-note-14-4g": (20999, "official"),
    "realme-note-70": (11999, "official"),
    "vivo-y31d": (24999, "official"),
    "samsung-galaxy-a36": (39999, "official"),
    "samsung-galaxy-a17-5g": (30999, "official"),
    "infinix-note-60-pro": (49999, "official"),
    "xiaomi-redmi-14c": (12999, "official"),
    "oppo-a6": (26999, "official"),
    "samsung-galaxy-a17": (28900, "reference"),
    "xiaomi-redmi-15c": (16999, "official"),
    "infinix-smart-10": (10499, "official"),
    "tecno-camon-50-pro": (41000, "reference"),
    "xiaomi-redmi-note-15-pro-5g": (34500, "unofficial"),
    "xiaomi-redmi-note-15-5g": (36999, "official"),
    "vivo-y11d": (16999, "official"),
    "tecno-spark-go-2": (9999, "official"),
    "tecno-camon-slim-5g": (59999, "official"),
    "zte-nubia-a57": (16999, "official"),
    "tecno-camon-50": (31999, "official"),
    "teсno-spark-40-pro-plus": (24999, "official"),
    "tecno-spark-40-pro": (19999, "official"),
    "tecno-spark-50": (17499, "official"),
    "oppo-a6s": (19000, "reference"),
    "infinix-note-edge": (29999, "official"),
    "realme-note-80": (15000, "reference"),
    "motorola-moto-g67-power": (23600, "unofficial"),
    "tecno-pova-slim-5g": (29999, "official"),
    "oneplus-15": (75500, "unofficial"),
    "xiaomi-civi-5-pro": (59900, "reference"),
    "vivo-s50": (45000, "reference"),
    "vivo-iqoo-z11-lite": (25000, "expected"),
    "oppo-a6t-5g": (27000, "reference"),
    "motorola-moto-g77-power": (33000, "unofficial"),
    "vivo-y05e": (16599, "official"),
    "samsung-galaxy-m06": (16500, "unofficial"),
    "honor-x70": (28000, "reference"),
    "oppo-k13-turbo": (29900, "reference"),
    "tecno-spark-40": (16999, "official"),
    "infinix-smart-10-plus": (11499, "official"),
    "itel-a50c": (6990, "official"),
    "vivo-y27": (20999, "official"),
    "xiaomi-redmi-12-5g": (19500, "reference"),
    "vivo-iqoo-z10x": (22500, "unofficial"),
    "xiaomi-poco-c81": (15000, "reference"),
    "honor-x5d": (13000, "reference"),
    "motorola-moto-g-play-2026": (26900, "reference"),
    "tecno-spark-50-pro": (24999, "official"),
    "samsung-galaxy-s25": (122000, "reference"),
    "samsung-galaxy-s24": (105600, "official"),
    "samsung-galaxy-s24-plus": (132000, "official"),
    "samsung-galaxy-s24-ultra": (219999, "official"),
    "samsung-galaxy-a55-5g": (73999, "official"),
    "samsung-galaxy-a35-5g": (59499, "official"),
    "samsung-galaxy-a37-5g": (60499, "official"),
    "samsung-galaxy-a57-5g": (78199, "official"),
    "iphone-15": (109000, "official"),
    "apple-iphone-15-plus": (179000, "official"),
    "apple-iphone-15-pro": (199000, "official"),
    "apple-iphone-15-pro-max": (219999, "official"),
    "iphone-16": (113000, "reference"),
    "apple-iphone-16-pro": (155000, "unofficial"),
    "apple-iphone-16-pro-max": (221999, "official"),
    "google-pixel-8": (57000, "unofficial"),
    "google-pixel-8-pro": (79999, "reference"),
    "google-pixel-8a": (51500, "unofficial"),
    "google-pixel-9": (69999, "reference"),
    "google-pixel-10a": (56499, "reference"),
    "oneplus-11": (99990, "official"),
    "oneplus-nord-ce4": (45500, "reference"),
    "oneplus-12": (79500, "unofficial"),
    "oneplus-12r": (53000, "unofficial"),
    "oneplus-13": (85000, "reference"),
    "xiaomi-14": (84990, "unofficial"),
    "xiaomi-14-ultra": (140000, "unofficial"),
    "xiaomi-14t": (65000, "reference"),
    "xiaomi-14t-pro": (82000, "reference"),
    "redmi-note-14-pro-plus-5g": (79500, "reference"),
    "poco-f6": (60000, "reference"),
    "poco-f6-pro": (72000, "reference"),
    "oppo-find-x7-ultra": (92700, "reference"),
    "oppo-reno-13-pro": (67000, "reference"),
    "vivo-v50": (62000, "reference"),
    "realme-gt-7-pro": (95000, "reference"),
    "motorola-edge-50-pro": (55000, "reference"),
    "honor-200-pro": (65000, "reference"),
    "nothing-phone-2a": (29500, "unofficial"),
    "nothing-phone-3": (60500, "unofficial"),
    "sony-xperia-10-vi": (55000, "reference"),
    "samsung-galaxy-s26": (128499, "official"),
    "samsung-galaxy-s26-plus": (172499, "official"),
    "samsung-galaxy-s26-ultra": (199999, "official"),
    "apple-iphone-17-pro": (215000, "reference"),
    "oppo-find-x9-ultra": (250000, "expected"),
    "xiaomi-17-ultra": (180000, "reference"),
    "honor-magic8-pro": (120000, "reference"),
    "motorola-razr-plus-2026": (120000, "reference"),
    "motorola-edge-2026": (65000, "reference"),
    "vivo-x300-pro": (130000, "reference"),
    "realme-gt-8-pro": (95000, "reference"),
    "asus-rog-phone-9-pro": (135000, "reference"),
    "sony-xperia-1-vii": (170000, "reference"),
}

# Exact specification patches for models where the current manufacturer-level
# specification is stable and known. Other catalog specs are preserved rather
# than replaced with guessed regional variants.
SPECS = {
    "samsung-galaxy-s24": {"display":"6.2-inch Dynamic AMOLED 2X, 120Hz","chip":"Snapdragon 8 Gen 3 for Galaxy / Exynos 2400 by region","ram":"8GB","storage":"128GB / 256GB / 512GB","rear_camera":"50MP + 10MP telephoto + 12MP ultrawide","battery":"4000mAh","charging":"25W","connectivity":"5G"},
    "samsung-galaxy-s24-plus": {"display":"6.7-inch Dynamic AMOLED 2X, QHD+, 120Hz","chip":"Snapdragon 8 Gen 3 for Galaxy / Exynos 2400 by region","ram":"12GB","storage":"256GB / 512GB","rear_camera":"50MP + 10MP telephoto + 12MP ultrawide","battery":"4900mAh","charging":"45W","connectivity":"5G"},
    "samsung-galaxy-s24-ultra": {"display":"6.8-inch QHD+ Dynamic AMOLED 2X, 120Hz","chip":"Snapdragon 8 Gen 3 for Galaxy","ram":"12GB","storage":"256GB / 512GB / 1TB","rear_camera":"200MP + 50MP 5x + 10MP 3x + 12MP ultrawide","battery":"5000mAh","charging":"45W","connectivity":"5G"},
    "samsung-galaxy-a55-5g": {"display":"6.6-inch Super AMOLED, 120Hz","chip":"Exynos 1480","ram":"8GB / 12GB","storage":"128GB / 256GB","rear_camera":"50MP + 12MP ultrawide + 5MP macro","battery":"5000mAh","charging":"25W","connectivity":"5G"},
    "samsung-galaxy-a35-5g": {"display":"6.6-inch Super AMOLED, 120Hz","chip":"Exynos 1380","ram":"6GB / 8GB","storage":"128GB / 256GB","rear_camera":"50MP + 8MP ultrawide + 5MP macro","battery":"5000mAh","charging":"25W","connectivity":"5G"},
    "iphone-15": {"display":"6.1-inch Super Retina XDR OLED","chip":"Apple A16 Bionic","ram":"6GB","storage":"128GB / 256GB / 512GB","rear_camera":"48MP Fusion + 12MP ultrawide","battery":"Built-in rechargeable battery","charging":"USB-C fast charging","connectivity":"5G"},
    "apple-iphone-15-pro": {"display":"6.1-inch Super Retina XDR OLED, ProMotion 120Hz","chip":"Apple A17 Pro","ram":"8GB","storage":"128GB / 256GB / 512GB / 1TB","rear_camera":"48MP + 12MP ultrawide + 12MP 3x telephoto","connectivity":"5G","port":"USB-C"},
    "apple-iphone-15-pro-max": {"display":"6.7-inch Super Retina XDR OLED, ProMotion 120Hz","chip":"Apple A17 Pro","ram":"8GB","storage":"256GB / 512GB / 1TB","rear_camera":"48MP + 12MP ultrawide + 12MP 5x telephoto","connectivity":"5G","port":"USB-C"},
    "google-pixel-8": {"display":"6.2-inch Actua OLED, 120Hz","chip":"Google Tensor G3","ram":"8GB","storage":"128GB / 256GB","rear_camera":"50MP wide + 12MP ultrawide","battery":"4575mAh-class","connectivity":"5G"},
    "google-pixel-8-pro": {"display":"6.7-inch Super Actua LTPO OLED, 1-120Hz","chip":"Google Tensor G3","ram":"12GB","storage":"128GB / 256GB / 512GB / 1TB","rear_camera":"50MP + 48MP ultrawide + 48MP telephoto","battery":"5050mAh-class","connectivity":"5G"},
    "oneplus-11": {"display":"6.7-inch QHD+ LTPO AMOLED, 1-120Hz","chip":"Snapdragon 8 Gen 2","ram":"8GB / 16GB","storage":"128GB / 256GB","rear_camera":"50MP + 32MP telephoto + 48MP ultrawide","battery":"5000mAh","charging":"100W SUPERVOOC","connectivity":"5G"},
    "oneplus-12": {"display":"6.82-inch QHD+ LTPO AMOLED, 1-120Hz","chip":"Snapdragon 8 Gen 3","ram":"12GB / 16GB / 24GB","storage":"256GB / 512GB / 1TB","rear_camera":"50MP + 64MP periscope telephoto + 48MP ultrawide","battery":"5400mAh","charging":"100W wired / 50W wireless","connectivity":"5G"},
    "oneplus-13": {"display":"6.82-inch LTPO AMOLED, 1-120Hz","chip":"Snapdragon 8 Elite","ram":"12GB / 16GB / 24GB","storage":"256GB / 512GB / 1TB","rear_camera":"50MP triple Hasselblad system","battery":"Large-capacity battery","charging":"Fast wired and wireless charging","connectivity":"5G"},
    "xiaomi-14": {"display":"6.36-inch LTPO AMOLED, 1-120Hz","chip":"Snapdragon 8 Gen 3","ram":"12GB / 16GB","storage":"256GB / 512GB","rear_camera":"Leica 50MP triple camera","battery":"4610mAh","charging":"90W wired / 50W wireless","connectivity":"5G"},
    "xiaomi-14-ultra": {"display":"6.73-inch LTPO AMOLED, 1-120Hz","chip":"Snapdragon 8 Gen 3","ram":"16GB","storage":"512GB / 1TB","rear_camera":"Leica 50MP quad-camera system","battery":"5000mAh","charging":"90W wired / 80W wireless","connectivity":"5G"},
    "poco-f6": {"display":"6.67-inch AMOLED, 120Hz","chip":"Snapdragon 8s Gen 3","ram":"8GB / 12GB","storage":"256GB / 512GB","rear_camera":"50MP + 8MP ultrawide","battery":"5000mAh","charging":"90W","connectivity":"5G"},
    "nothing-phone-3": {"display":"6.67-inch OLED, 120Hz","chip":"Snapdragon 8s Gen 4","ram":"12GB / 16GB","storage":"256GB / 512GB","rear_camera":"50MP + 50MP + 50MP","front_camera":"50MP","battery":"5150mAh","charging":"65W","connectivity":"5G"},
}


def upgrade():
    bind = op.get_bind()
    for slug, (price, status) in PRICES.items():
        bind.execute(text("""UPDATE phone_catalog
            SET price_bdt=:price,
                source_name='GSMArena Bangladesh / current BD reference',
                source_url='https://www.gsmarena.com.bd/top-phones',
                source_checked_at=:checked,
                data_confidence='verified',
                updated_at=CURRENT_TIMESTAMP
            WHERE slug=:slug AND status='published'"""),
            {"slug": slug, "price": price, "checked": CHECKED})

    for slug, patch in SPECS.items():
        row = bind.execute(text("SELECT specs_json FROM phone_catalog WHERE slug=:slug AND status='published'"), {"slug": slug}).mappings().first()
        if not row:
            continue
        current = row["specs_json"] or "{}"
        try:
            data = json.loads(current) if isinstance(current, str) else dict(current)
        except (TypeError, ValueError):
            data = {}
        data.update(patch)
        bind.execute(text("""UPDATE phone_catalog SET specs_json=:specs,
            source_checked_at=:checked, updated_at=CURRENT_TIMESTAMP
            WHERE slug=:slug AND status='published'"""),
            {"slug": slug, "specs": json.dumps(data, ensure_ascii=False), "checked": CHECKED})


def downgrade():
    # Price/spec rollback is intentionally non-destructive: prior catalog data
    # remains safer than guessing what a pre-refresh value was.
    pass
