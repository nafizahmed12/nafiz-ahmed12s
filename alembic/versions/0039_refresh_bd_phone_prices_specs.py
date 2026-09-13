"""Refresh current Bangladesh phone prices for catalog models.

Revision ID: 0039_bd_price_refresh
Revises: 0038_verified_bd_phone_prices
"""
from datetime import datetime

from alembic import op
from sqlalchemy import text

revision = "0039_bd_price_refresh"
down_revision = "0038_verified_bd_phone_prices"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 13)

REFRESH = {
    "samsung-galaxy-s24": (105600, "official", "https://www.gsmarena.com.bd/samsung-galaxy-s24/"),
    "samsung-galaxy-s24-plus": (132000, "official", "https://www.gsmarena.com.bd/samsung-galaxy-s24-plus/"),
    "samsung-galaxy-s24-ultra": (219999, "official", "https://www.gsmarena.com.bd/samsung-galaxy-s24-ultra/"),
    "samsung-galaxy-a55-5g": (73999, "official", "https://www.gsmarena.com.bd/samsung-galaxy-a55-5g/"),
    "samsung-galaxy-a35-5g": (59499, "official", "https://www.gsmarena.com.bd/samsung-galaxy-a35/"),
    "samsung-galaxy-a37-5g": (60499, "official", "https://www.gsmarena.com.bd/official/"),
    "samsung-galaxy-a57-5g": (78199, "official", "https://www.gsmarena.com.bd/official/"),
    "iphone-15": (109000, "official", "https://www.gsmarena.com.bd/apple/"),
    "apple-iphone-15-plus": (179000, "official", "https://www.gsmarena.com.bd/apple/"),
    "apple-iphone-15-pro": (199000, "official", "https://www.gsmarena.com.bd/apple/"),
    "apple-iphone-15-pro-max": (219999, "official", "https://www.gsmarena.com.bd/apple/"),
    "iphone-16": (113000, "reference", "https://www.gsmarena.com.bd/compare/apple-iphone-16-pro-max-vs-apple-iphone-16/"),
    "apple-iphone-16-pro": (155000, "unofficial", "https://www.gsmarena.com.bd/compare/apple-iphone-16-pro-max-vs-apple-iphone-16-pro/"),
    "apple-iphone-16-pro-max": (221999, "official", "https://www.gsmarena.com.bd/apple-iphone-16-pro-max/"),
    "google-pixel-8": (57000, "unofficial", "https://www.gsmarena.com.bd/google-pixel-8/"),
    "google-pixel-8-pro": (79999, "reference", "https://www.gsmarena.com.bd/compare/google-pixel-8-pro-vs-apple-iphone-15-pro/"),
    "google-pixel-8a": (51500, "unofficial", "https://www.gsmarena.com.bd/price-range/40000-250000/11"),
    "oneplus-11": (99990, "official", "https://www.gsmarena.com.bd/oneplus/"),
    "oneplus-nord-ce4": (45500, "reference", "https://www.gsmarena.com.bd/compare/oneplus-nord-ce4-vs-xiaomi-redmi-note-14/"),
    "xiaomi-14": (84990, "unofficial", "https://www.gsmarena.com.bd/price-range/40000-250000/11"),
    "xiaomi-14-ultra": (140000, "unofficial", "https://www.gsmarena.com.bd/price-range/40000-250000/11"),
    "redmi-note-14-pro-plus-5g": (79500, "reference", "https://www.gsmarena.com.bd/compare/samsung-galaxy-a55-5g-vs-xiaomi-redmi-note-14-pro-plus-5g-global/"),
    "poco-f6": (60000, "reference", "https://www.gsmarena.com.bd/xiaomi-poco-f6/"),
    "oppo-find-x7-ultra": (92700, "reference", "https://www.gsmarena.com.bd/price-range/40000-250000/11"),
}


def upgrade():
    bind = op.get_bind()
    for slug, (price, status, url) in REFRESH.items():
        bind.execute(
            text(
                """UPDATE phone_catalog
                SET price_bdt=:price,
                    source_name=:source,
                    source_url=:url,
                    source_checked_at=:checked,
                    data_confidence='verified',
                    updated_at=CURRENT_TIMESTAMP
                WHERE slug=:slug AND status='published'"""
            ),
            {
                "slug": slug,
                "price": price,
                "source": f"GSMArena Bangladesh ({status})",
                "url": url,
                "checked": CHECKED,
            },
        )


def downgrade():
    pass
