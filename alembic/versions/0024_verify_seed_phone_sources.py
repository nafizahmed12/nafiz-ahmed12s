"""Attach official provenance to the initial phone catalog and add iPhone 17e."""
from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime

revision = "0024_verify_seed_phone_sources"
down_revision = "0023_phone_data_provenance"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 9, 0, 0, 0)
SOURCES = {
    "apple-iphone-17": ("Apple", "https://www.apple.com/iphone-17/specs/"),
    "apple-iphone-17-pro": ("Apple", "https://www.apple.com/iphone-17-pro/specs/"),
    "apple-iphone-17-pro-max": ("Apple", "https://www.apple.com/iphone-17-pro/specs/"),
    "google-pixel-10": ("Google Store", "https://store.google.com/product/pixel_10"),
    "xiaomi-15-ultra": ("Xiaomi", "https://www.mi.com/global/xiaomi-15-ultra/"),
    "motorola-razr-60-ultra": ("Motorola Support", "https://en-us.support.motorola.com/app/answers/detail/a_id/187134/~/specifications---motorola-razr-60-ultra"),
    "huawei-pura-80-ultra": ("HUAWEI", "https://consumer.huawei.com/sg/phones/pura80-ultra/specs/"),
    "honor-magic7-pro": ("HONOR", "https://www.honor.com/global/phones/honor-magic7-pro/"),
    "nothing-phone-3": ("Nothing", "https://nothing.tech/pages/phone-3"),
}

NEW_PHONE = {
    "brand": "Apple", "model": "iPhone 17e", "slug": "apple-iphone-17e",
    "description": "Apple iPhone 17e specifications, A19 chip, 6.1-inch OLED display, camera, battery and connectivity details.",
    "content": "The iPhone 17e is a 2026 Apple smartphone with a 6.1-inch Super Retina XDR OLED display and the A19 chip. Apple lists 256GB and 512GB storage options, IP68 water and dust resistance, a 12MP TrueDepth front camera and USB-C connectivity. Apple also specifies up to 26 hours of video playback and MagSafe and Qi2 wireless charging up to 15W. The phone uses eSIM rather than a physical SIM card, and cellular support can vary by model and region.",
    "release_date": "2026",
    "specs": {"display":"6.1-inch Super Retina XDR OLED, 2532x1170, 460 ppi", "chip":"Apple A19", "storage":"256GB / 512GB", "rear_camera":"48MP Fusion camera", "front_camera":"12MP TrueDepth", "battery":"Up to 26 hours video playback", "charging":"USB-C; MagSafe/Qi2 up to 15W", "water_resistance":"IP68", "os":"iOS 26"},
    "source_name": "Apple", "source_url": "https://www.apple.com/iphone-17e/specs/",
}

def upgrade():
    conn = op.get_bind()
    for slug, (name, url) in SOURCES.items():
        conn.execute(sa.text("""UPDATE phone_catalog SET source_name=:name, source_url=:url, source_checked_at=:checked, data_confidence='official' WHERE slug=:slug"""), {"name": name, "url": url, "checked": CHECKED, "slug": slug})
    conn.execute(sa.text("""INSERT INTO phone_catalog
        (brand,model,slug,short_description,content,release_date,specs_json,status,seo_description,created_at,updated_at,published_at,source_name,source_url,source_checked_at,data_confidence)
        VALUES (:brand,:model,:slug,:description,:content,:release_date,:specs_json,'published',:description,:created_at,:updated_at,:published_at,:source_name,:source_url,:source_checked_at,'official')
        ON CONFLICT (slug) DO UPDATE SET source_name=EXCLUDED.source_name, source_url=EXCLUDED.source_url, source_checked_at=EXCLUDED.source_checked_at, data_confidence='official'"""), {"brand":NEW_PHONE["brand"],"model":NEW_PHONE["model"],"slug":NEW_PHONE["slug"],"description":NEW_PHONE["description"],"content":NEW_PHONE["content"],"release_date":NEW_PHONE["release_date"],"specs_json":json.dumps(NEW_PHONE["specs"],ensure_ascii=False),"created_at":CHECKED,"updated_at":CHECKED,"published_at":CHECKED,"source_name":NEW_PHONE["source_name"],"source_url":NEW_PHONE["source_url"],"source_checked_at":CHECKED})

def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM phone_catalog WHERE slug=:slug"), {"slug":NEW_PHONE["slug"]})
    for slug in SOURCES:
        conn.execute(sa.text("UPDATE phone_catalog SET source_name=NULL,source_url=NULL,source_checked_at=NULL,data_confidence='unverified' WHERE slug=:slug"), {"slug":slug})
