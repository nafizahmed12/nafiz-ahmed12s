"""Populate verified Bangladesh prices, specs and storage variants for catalog phones.

Revision ID: 0038_verified_bd_phone_prices
Revises: 0037_fix_phone_catalog_images
"""
from datetime import datetime
import json

from alembic import op
from sqlalchemy import text

revision = "0038_verified_bd_phone_prices"
down_revision = "0037_fix_phone_catalog_images"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 13, 0, 0, 0)

PHONES = [
    {
        "slug": "samsung-galaxy-s26",
        "price": "128499",
        "source": "Star Tech Bangladesh",
        "url": "https://www.startech.com.bd/samsung-galaxy-s26",
        "specs": {"category":"Flagship","display":"6.3-inch Dynamic LTPO AMOLED 2X, 120Hz","chip":"Snapdragon 8 Elite Gen 5","ram":"12GB","storage":"256GB","rear_camera":"50MP wide + 10MP 3x telephoto + 12MP ultrawide","front_camera":"12MP","battery":"4300mAh","charging":"25W wired, 15W wireless","water_resistance":"IP68","os":"Android 16 / One UI 8.5","variants":[{"ram":"12GB","storage":"256GB","price_bdt":128499}]},
    },
    {
        "slug": "samsung-galaxy-a57-5g",
        "price": "69950",
        "source": "Star Tech Bangladesh",
        "url": "https://www.startech.com.bd/samsung-galaxy-a57",
        "specs": {"category":"Upper mid-range","display":"6.7-inch FHD+ Super AMOLED, 120Hz","chip":"Exynos 1680","ram":"8GB / 12GB","storage":"128GB / 256GB","rear_camera":"50MP OIS + 12MP ultrawide + 5MP macro","front_camera":"12MP","battery":"5000mAh","charging":"45W","water_resistance":"IP68","os":"Android 16 / One UI 8.5","variants":[{"ram":"8GB","storage":"256GB","price_bdt":69950},{"ram":"12GB","storage":"256GB","price_bdt":69950}]},
    },
    {
        "slug": "samsung-galaxy-a37-5g",
        "price": "52250",
        "source": "Star Tech Bangladesh",
        "url": "https://www.startech.com.bd/samsung-galaxy-a37",
        "specs": {"category":"Mid-range","display":"6.7-inch FHD+ Super AMOLED, 120Hz","chip":"Exynos 1480","ram":"8GB / 12GB","storage":"128GB / 256GB","rear_camera":"50MP OIS + 8MP ultrawide + 5MP macro","front_camera":"12MP","battery":"5000mAh","charging":"45W","water_resistance":"IP68","os":"Android 16 / One UI 8.5","variants":[{"ram":"8GB","storage":"128GB","price_bdt":52250},{"ram":"8GB","storage":"256GB","price_bdt":52250}]},
    },
    {
        "slug": "samsung-galaxy-a17-5g",
        "price": "31550",
        "source": "Star Tech Bangladesh",
        "url": "https://www.startech.com.bd/samsung-galaxy-a17-5g",
        "specs": {"category":"Affordable 5G","display":"6.7-inch Super AMOLED, 90Hz","chip":"Exynos 1330","ram":"6GB / 8GB","storage":"128GB / 256GB","rear_camera":"50MP OIS + 5MP ultrawide + 2MP macro","front_camera":"13MP","battery":"5000mAh","charging":"25W","water_resistance":"IP54","os":"Android 15 / One UI 7","variants":[{"ram":"6GB","storage":"128GB","price_bdt":31550},{"ram":"8GB","storage":"128GB","price_bdt":31550},{"ram":"8GB","storage":"256GB","price_bdt":31550}]},
    },
    {
        "slug": "iphone-16",
        "price": "89999",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/iphone",
        "specs": {"category":"Premium","display":"6.1-inch Super Retina XDR OLED","chip":"Apple A18","ram":"8GB","storage":"128GB / 256GB / 512GB","rear_camera":"48MP wide + 12MP ultrawide","front_camera":"12MP","battery":"3561mAh","charging":"USB-C, MagSafe","water_resistance":"IP68","os":"iOS","variants":[{"ram":"8GB","storage":"128GB","price_bdt":89999},{"ram":"8GB","storage":"256GB","price_bdt":89999},{"ram":"8GB","storage":"512GB","price_bdt":89999}]},
    },
    {
        "slug": "iphone-15",
        "price": "80999",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/iphone",
        "specs": {"category":"Premium","display":"6.1-inch Super Retina XDR OLED","chip":"Apple A16 Bionic","ram":"6GB","storage":"128GB / 256GB / 512GB","rear_camera":"48MP wide + 12MP ultrawide","front_camera":"12MP","battery":"3349mAh","charging":"USB-C, MagSafe","water_resistance":"IP68","os":"iOS","variants":[{"ram":"6GB","storage":"128GB","price_bdt":80999},{"ram":"6GB","storage":"256GB","price_bdt":80999},{"ram":"6GB","storage":"512GB","price_bdt":80999}]},
    },
    {
        "slug": "apple-iphone-air",
        "price": "113999",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/iphone",
        "specs": {"category":"Premium","display":"6.5-inch LTPO Super Retina XDR OLED, 120Hz","chip":"Apple A19 Pro","ram":"12GB","storage":"256GB / 512GB / 1TB","rear_camera":"48MP wide","front_camera":"18MP","battery":"3149mAh","charging":"USB-C, MagSafe / Qi2","water_resistance":"IP68","os":"iOS 26","variants":[{"ram":"12GB","storage":"256GB","price_bdt":113999},{"ram":"12GB","storage":"512GB","price_bdt":113999},{"ram":"12GB","storage":"1TB","price_bdt":113999}]},
    },
    {
        "slug": "google-pixel-10-pro",
        "price": "96500",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/google",
        "specs": {"category":"Flagship","display":"6.3-inch LTPO OLED, 1-120Hz","chip":"Google Tensor G5","ram":"16GB","storage":"128GB / 256GB / 512GB / 1TB","rear_camera":"50MP wide + 48MP ultrawide + 48MP 5x telephoto","front_camera":"42MP","battery":"4870mAh","charging":"30W wired / 15W wireless","water_resistance":"IP68","os":"Android","variants":[{"ram":"16GB","storage":"128GB","price_bdt":96500},{"ram":"16GB","storage":"256GB","price_bdt":105000},{"ram":"16GB","storage":"512GB","price_bdt":129500},{"ram":"16GB","storage":"1TB","price_bdt":140000}]},
    },
    {
        "slug": "google-pixel-9",
        "price": "69999",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/google",
        "specs": {"category":"Flagship","display":"6.3-inch OLED Actua display","chip":"Google Tensor G4","storage":"128GB / 256GB","rear_camera":"50MP wide + 48MP ultrawide","front_camera":"10.5MP","battery":"4700mAh-class","charging":"27W wired / wireless","water_resistance":"IP68","os":"Android","variants":[{"storage":"128GB","price_bdt":69999},{"storage":"256GB","price_bdt":69999}]},
    },
    {
        "slug": "google-pixel-10a",
        "price": "56499",
        "source": "Apple Gadgets Bangladesh",
        "url": "https://www.applegadgetsbd.com/category/mobile-phone/google",
        "specs": {"category":"Value flagship","display":"OLED-class display","chip":"Google Tensor platform","storage":"128GB / 256GB","rear_camera":"Pixel dual-camera system","os":"Android","variants":[{"storage":"128GB","price_bdt":56499},{"storage":"256GB","price_bdt":56499}]},
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    for phone in PHONES:
        bind.execute(
            text("""UPDATE phone_catalog
               SET price_bdt=:price,
                   specs_json=:specs,
                   source_name=:source,
                   source_url=:url,
                   source_checked_at=:checked,
                   data_confidence='verified',
                   updated_at=CURRENT_TIMESTAMP
             WHERE slug=:slug"""),
            {
                "slug": phone["slug"],
                "price": phone["price"],
                "specs": json.dumps(phone["specs"], ensure_ascii=False),
                "source": phone["source"],
                "url": phone["url"],
                "checked": CHECKED,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    for phone in PHONES:
        bind.execute(
            text("""UPDATE phone_catalog
               SET price_bdt=NULL,
                   source_checked_at=NULL,
                   data_confidence='unverified'
             WHERE slug=:slug"""),
            {"slug": phone["slug"]},
        )
