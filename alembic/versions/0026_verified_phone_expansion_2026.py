"""Add a curated batch of manufacturer-verified 2026 phone pages."""
from alembic import op
import json
from datetime import datetime

revision = "0026_phone_expansion_2026"
down_revision = "0025_verified_phone_expansion_20"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 9, 0, 0, 0)

PHONES = [
    {"brand":"Samsung","model":"Galaxy S26","slug":"samsung-galaxy-s26","desc":"Samsung Galaxy S26 specifications, 6.3-inch Dynamic AMOLED 2X display, Snapdragon or Exynos performance and triple cameras.","content":"The Galaxy S26 is Samsung's 2026 compact flagship, combining a 6.3-inch Dynamic AMOLED 2X display with adaptive 120Hz refresh and a flagship processor that varies by market. Samsung lists 12GB memory with 256GB or 512GB storage, a 4300mAh typical battery and a triple rear camera system with 3x optical zoom. Regional chipset and configuration differences should be checked before purchase.","specs":{"display":"6.3-inch Dynamic AMOLED 2X, FHD+, 1-120Hz","chip":"Snapdragon 8 Elite Gen 5 for Galaxy or Exynos 2600","ram":"12GB","storage":"256GB / 512GB","rear_camera":"50MP wide + 10MP 3x telephoto + 12MP ultrawide","battery":"4300mAh typical","water_resistance":"IP68","os":"Android"},"source":"Samsung Bangladesh","url":"https://www.samsung.com/bd/smartphones/galaxy-s26/specs/"},
    {"brand":"Samsung","model":"Galaxy S26+","slug":"samsung-galaxy-s26-plus","desc":"Samsung Galaxy S26+ specifications, 6.7-inch QHD+ AMOLED display, flagship processor, cameras and 4900mAh battery.","content":"The Galaxy S26+ expands Samsung's 2026 flagship range with a 6.7-inch QHD+ Dynamic AMOLED 2X display and adaptive 120Hz refresh. Samsung lists 12GB RAM with 256GB or 512GB storage and a 4900mAh typical battery. Its rear camera system combines a 50MP main camera, 10MP 3x telephoto and 12MP ultrawide, while exact processor availability can vary by market.","specs":{"display":"6.7-inch Dynamic AMOLED 2X, QHD+, 1-120Hz","chip":"Snapdragon 8 Elite Gen 5 for Galaxy or Exynos 2600","ram":"12GB","storage":"256GB / 512GB","rear_camera":"50MP wide + 10MP 3x telephoto + 12MP ultrawide","battery":"4900mAh typical","water_resistance":"IP68","os":"Android"},"source":"Samsung Bangladesh","url":"https://www.samsung.com/bd/smartphones/galaxy-s26/specs/"},
    {"brand":"Apple","model":"iPhone Air","slug":"apple-iphone-air","desc":"Apple iPhone Air specifications, 6.5-inch ProMotion OLED display, A19 Pro chip, 256GB to 1TB storage and IP68 protection.","content":"The iPhone Air is Apple's thin 2026 iPhone model, built around a 6.5-inch Super Retina XDR OLED display with ProMotion up to 120Hz. Apple lists the A19 Pro chip, 256GB, 512GB or 1TB storage, a titanium design and IP68 water and dust resistance. Its 5.64mm thickness and 165g weight make the model especially relevant for buyers prioritizing a lightweight, thin flagship design.","specs":{"display":"6.5-inch Super Retina XDR OLED, ProMotion up to 120Hz","chip":"Apple A19 Pro","storage":"256GB / 512GB / 1TB","weight":"165g","thickness":"5.64mm","water_resistance":"IP68","os":"iOS"},"source":"Apple","url":"https://www.apple.com/iphone-air/specs/"},
    {"brand":"Google","model":"Pixel 10 Pro","slug":"google-pixel-10-pro","desc":"Google Pixel 10 Pro specifications, Tensor G5, 6.3-inch LTPO OLED display, 16GB RAM and triple rear cameras.","content":"The Pixel 10 Pro is Google's compact 2026 Pro flagship with a 6.3-inch Super Actua LTPO OLED display running from 1Hz to 120Hz. Google lists the Tensor G5 processor, 16GB RAM and storage options from 128GB through 1TB. Its Pro triple camera system combines 50MP wide, 48MP ultrawide and 48MP 5x telephoto cameras, backed by Google's computational photography features.","specs":{"display":"6.3-inch Super Actua LTPO OLED, 1-120Hz","chip":"Google Tensor G5","ram":"16GB","storage":"128GB / 256GB / 512GB / 1TB","rear_camera":"50MP wide + 48MP ultrawide + 48MP 5x telephoto","battery":"4870mAh typical","charging":"30W wired / 15W Qi2","os":"Android"},"source":"Google Store","url":"https://store.google.com/us/product/pixel_10_pro_specs?hl=en-US"},
]


def upgrade():
    bind = op.get_bind()
    for phone in PHONES:
        exists = bind.execute(__import__('sqlalchemy').text("SELECT id FROM phone_catalog WHERE slug=:slug"), {"slug": phone["slug"]}).first()
        if exists:
            continue
        bind.execute(__import__('sqlalchemy').text("""INSERT INTO phone_catalog (brand,model,slug,short_description,content,image_url,release_date,price_usd,price_bdt,specs_json,status,seo_description,published_at,source_name,source_url,source_checked_at,data_confidence)
        VALUES (:brand,:model,:slug,:short_description,:content,NULL,:release_date,NULL,NULL,:specs_json,'published',:seo_description,:published_at,:source_name,:source_url,:source_checked_at,'official')"""), {"brand":phone["brand"],"model":phone["model"],"slug":phone["slug"],"short_description":phone["desc"],"content":phone["content"],"release_date":"2026","specs_json":json.dumps(phone["specs"]),"seo_description":phone["desc"],"published_at":CHECKED,"source_name":phone["source"],"source_url":phone["url"],"source_checked_at":CHECKED})


def downgrade():
    bind = op.get_bind()
    for phone in PHONES:
        bind.execute(__import__('sqlalchemy').text("DELETE FROM phone_catalog WHERE slug=:slug"), {"slug": phone["slug"]})
