"""Seed the first curated global phone catalog batch.

The migration intentionally publishes a small set of well-defined models and
keeps the catalog expandable. It avoids generating hundreds of thin pages.
"""
from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime

revision = "0022_seed_phone_catalog"
down_revision = "0021_phone_catalog"
branch_labels = None
depends_on = None

PUBLISHED = [
    {
        "brand": "Apple", "model": "iPhone 17", "slug": "apple-iphone-17",
        "description": "Apple iPhone 17 specifications, display, A19 chip, camera, battery, storage and key features in one place.",
        "content": "The iPhone 17 is a 2025 Apple smartphone focused on a 6.3-inch OLED display, the A19 chip and a modern dual-camera system. Apple lists 256GB and 512GB storage options, ProMotion up to 120Hz, IP68 water and dust resistance, and Apple Intelligence support. This page is designed as a quick reference for the model's core hardware and software characteristics. Availability, configuration and regional network support can vary by market, so buyers should confirm local details before purchasing.",
        "release_date": "2025", "specs": {"display":"6.3-inch OLED, up to 120Hz","chip":"Apple A19","storage":"256GB / 512GB","water_resistance":"IP68","os":"iOS"},
    },
    {
        "brand": "Apple", "model": "iPhone 17 Pro", "slug": "apple-iphone-17-pro",
        "description": "Apple iPhone 17 Pro specifications, A19 Pro performance, Pro camera system, display and battery information.",
        "content": "The iPhone 17 Pro is Apple's professional 2025 model with a 6.3-inch Super Retina XDR OLED display and ProMotion up to 120Hz. Apple specifies the A19 Pro chip, a 48MP Pro Fusion camera system, IP68 protection and USB-C connectivity. Storage options include 256GB, 512GB and 1TB. The model also supports Apple Intelligence and satellite safety features in supported regions. Exact network bands and SIM configuration can vary by model and market.",
        "release_date": "2025", "specs": {"display":"6.3-inch Super Retina XDR OLED, up to 120Hz","chip":"Apple A19 Pro","storage":"256GB / 512GB / 1TB","main_camera":"48MP Pro Fusion system","water_resistance":"IP68"},
    },
    {
        "brand": "Apple", "model": "iPhone 17 Pro Max", "slug": "apple-iphone-17-pro-max",
        "description": "Apple iPhone 17 Pro Max specifications, 6.9-inch display, A19 Pro chip, cameras, storage and battery details.",
        "content": "The iPhone 17 Pro Max is Apple's largest 2025 Pro iPhone. It uses a 6.9-inch Super Retina XDR OLED display with ProMotion up to 120Hz and the A19 Pro chip. Apple lists storage capacities up to 2TB and a 48MP Pro Fusion camera system with a dedicated telephoto camera. The device has IP68 water and dust resistance, USB-C, Wi-Fi 7 and Apple Intelligence. Regional SIM, cellular-band and availability details should be checked against the exact model sold in the buyer's market.",
        "release_date": "2025", "specs": {"display":"6.9-inch Super Retina XDR OLED, up to 120Hz","chip":"Apple A19 Pro","storage":"256GB / 512GB / 1TB / 2TB","main_camera":"48MP Pro Fusion system","water_resistance":"IP68"},
    },
    {
        "brand": "Google", "model": "Pixel 10", "slug": "google-pixel-10",
        "description": "Google Pixel 10 specifications including its 6.3-inch OLED display, battery, charging and core hardware.",
        "content": "Google Pixel 10 is a 2025 Pixel smartphone with a 6.3-inch Actua OLED display and Smooth Display from 60Hz to 120Hz. Google lists a typical 4,970mAh battery, 24-plus-hour battery life and wired charging that can reach up to 55 percent in about 30 minutes with a compatible 30W USB-C PPS charger or higher. Pixel 10 also supports Qi2-certified wireless charging up to 15W. Regional configurations and network support should be verified before purchase.",
        "release_date": "2025", "specs": {"display":"6.3-inch Actua OLED, 60-120Hz","battery":"4970mAh typical","charging":"Up to 55% in about 30 minutes with compatible charger","wireless_charging":"Qi2 up to 15W","os":"Android"},
    },
    {
        "brand": "Xiaomi", "model": "Xiaomi 15 Ultra", "slug": "xiaomi-15-ultra",
        "description": "Xiaomi 15 Ultra specifications covering Snapdragon 8 Elite, WQHD+ AMOLED display, cameras, battery and charging.",
        "content": "The Xiaomi 15 Ultra is a flagship Android phone built around Qualcomm's Snapdragon 8 Elite Mobile Platform. Xiaomi lists a 6.73-inch WQHD+ AMOLED display with 1-120Hz refresh rate and up to 3200 nits multi-scenario peak brightness. The phone is offered in configurations including 16GB RAM with 512GB storage, while the battery is rated at 5410mAh with 90W wired and 80W wireless HyperCharge. Xiaomi also highlights a multi-camera system and advanced imaging features. Storage and regional configurations can differ.",
        "release_date": "2025", "specs": {"display":"6.73-inch WQHD+ AMOLED, 1-120Hz","chip":"Snapdragon 8 Elite","memory":"16GB RAM + 512GB / 1TB","battery":"5410mAh","charging":"90W wired / 80W wireless"},
    },
    {
        "brand": "Motorola", "model": "Razr 60 Ultra", "slug": "motorola-razr-60-ultra",
        "description": "Motorola Razr 60 Ultra specifications, foldable displays, Snapdragon 8 Elite, battery and charging details.",
        "content": "The Motorola Razr 60 Ultra is a foldable Android smartphone with a large internal display and a 4.0-inch external pOLED display. Motorola lists the Snapdragon 8 Elite platform, 16GB RAM, 512GB UFS 4.0 storage and a 4,700mAh battery. The main display supports up to 165Hz, while charging includes 68W wired and 30W wireless charging. The phone also supports Wi-Fi 7, Bluetooth 5.4 and IP48 protection. Some specifications and network bands can vary by market.",
        "release_date": "2025", "specs": {"main_display":"7.0-inch-class foldable LTPO AMOLED, up to 165Hz","cover_display":"4.0-inch pOLED","chip":"Snapdragon 8 Elite","memory":"16GB RAM + 512GB","battery":"4700mAh","charging":"68W wired / 30W wireless"},
    },
    {
        "brand": "Huawei", "model": "Pura 80 Ultra", "slug": "huawei-pura-80-ultra",
        "description": "Huawei Pura 80 Ultra specifications including LTPO OLED display, camera system, Kirin 9020 and charging.",
        "content": "The Huawei Pura 80 Ultra is a premium Huawei smartphone with a 6.8-inch LTPO OLED display supporting adaptive 1-120Hz refresh rates. Huawei lists the Kirin 9020 processor, 16GB RAM and 512GB storage in one published configuration. Its rear camera system includes a 50MP one-inch main camera, 40MP ultra-wide camera and telephoto cameras with optical zoom. The rated battery capacity is 5170mAh with up to 100W wired and 80W wireless Huawei SuperCharge. Regional software and configuration should be checked before purchase.",
        "release_date": "2025", "specs": {"display":"6.8-inch LTPO OLED, 1-120Hz","chip":"Kirin 9020","memory":"16GB RAM + 512GB","battery":"5170mAh","charging":"Up to 100W wired / 80W wireless","os":"EMUI 15.0"},
    },
    {
        "brand": "HONOR", "model": "Magic7 Pro", "slug": "honor-magic7-pro",
        "description": "HONOR Magic7 Pro specifications, Snapdragon 8 Elite, 6.8-inch display, 200MP telephoto and fast charging.",
        "content": "The HONOR Magic7 Pro is a flagship Android smartphone featuring the Snapdragon 8 Elite Mobile Platform. HONOR lists a 6.80-inch micro-quad-curved display with adaptive 1-120Hz refresh rate and high peak brightness. Its camera system includes a 200MP telephoto camera with 3x optical zoom, a 50MP main camera and a 50MP ultra-wide camera. HONOR also advertises a large silicon-carbon battery with up to 100W wired and 80W wireless SuperCharge. Features and availability can vary by region.",
        "release_date": "2025", "specs": {"display":"6.80-inch micro-quad-curved, 1-120Hz","chip":"Snapdragon 8 Elite","telephoto":"200MP, 3x optical zoom","main_camera":"50MP","charging":"Up to 100W wired / 80W wireless"},
    },
    {
        "brand": "Nothing", "model": "Phone (3)", "slug": "nothing-phone-3",
        "description": "Nothing Phone (3) specifications overview with dimensions, weight and key product information.",
        "content": "Nothing Phone (3) is a 2025 smartphone from Nothing with the company's distinctive design approach. Nothing's official support documentation lists dimensions of 160.6mm by 75.59mm by 8.99mm and a weight of 218 grams. This catalog entry focuses on the confirmed product identity and physical specifications while avoiding unsupported regional pricing or configuration claims. Buyers should check Nothing's official product documentation for the exact memory, connectivity and software configuration available in their market.",
        "release_date": "2025", "specs": {"height":"160.6mm","width":"75.59mm","thickness":"8.99mm","weight":"218g","os":"Android"},
    },
]


def upgrade():
    conn = op.get_bind()
    now = datetime.utcnow()
    for phone in PUBLISHED:
        conn.execute(sa.text("""INSERT INTO phone_catalog
            (brand, model, slug, short_description, content, release_date, specs_json, status, seo_description, created_at, updated_at, published_at)
            VALUES (:brand, :model, :slug, :description, :content, :release_date, :specs_json, 'published', :description, :created_at, :updated_at, :published_at)
            ON CONFLICT (slug) DO NOTHING"""), {
            "brand": phone["brand"], "model": phone["model"], "slug": phone["slug"],
            "description": phone["description"], "content": phone["content"],
            "release_date": phone["release_date"], "specs_json": json.dumps(phone["specs"], ensure_ascii=False),
            "created_at": now, "updated_at": now, "published_at": now,
        })


def downgrade():
    conn = op.get_bind()
    slugs = [p["slug"] for p in PUBLISHED]
    conn.execute(sa.text("DELETE FROM phone_catalog WHERE slug = ANY(:slugs)"), {"slugs": slugs})
