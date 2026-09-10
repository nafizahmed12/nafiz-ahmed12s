"""Add iPhone 18 Pro Max to the customer-facing catalog.

Revision ID: 0031_iphone_18_pro_max
Revises: 0030_popular_phone_coverage
"""

from alembic import op
from sqlalchemy import text


revision = "0031_iphone_18_pro_max"
down_revision = "0030_popular_phone_coverage"
branch_labels = None
depends_on = None

SLUG = "iphone-18-pro-max"
IMAGE_URL = "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?q=80&w=800&auto=format&fit=crop"


def upgrade() -> None:
    bind = op.get_bind()

    product_id = bind.execute(
        text("SELECT id FROM products WHERE slug=:slug LIMIT 1"),
        {"slug": SLUG},
    ).scalar_one_or_none()

    if product_id is None:
        product_id = bind.execute(
            text("""
                INSERT INTO products
                    (category_id,owner_id,name,slug,description,product_type,status,
                     price,currency,sku,stock_quantity,created_at,updated_at)
                VALUES
                    (NULL,NULL,:name,:slug,:description,'physical','published',
                     1299.00,'USD',:sku,0,NOW(),NOW())
                RETURNING id
            """),
            {
                "name": "iPhone 18 Pro Max",
                "slug": SLUG,
                "description": (
                    "Apple iPhone 18 Pro Max with A20 Pro, 48MP Fusion Main camera "
                    "with variable aperture, iOS 27, and up to 45 hours of video playback. "
                    "Pre-order starts September 12, 2026; availability starts September 18, 2026."
                ),
                "sku": "APPLE-IP18PM-256",
            },
        ).scalar_one()

    listing = bind.execute(
        text("SELECT id FROM product_listings WHERE product_id=:product_id LIMIT 1"),
        {"product_id": product_id},
    ).scalar_one_or_none()

    if listing is None:
        bind.execute(
            text("""
                INSERT INTO product_listings
                    (product_id,seller_id,supplier_product_id,listing_type,title,price,
                     compare_at_price,currency,stock_quantity,status,featured,created_at,updated_at)
                VALUES
                    (:product_id,NULL,NULL,'owned',:title,1299.00,NULL,'USD',0,
                     'published',TRUE,NOW(),NOW())
            """),
            {"product_id": product_id, "title": "iPhone 18 Pro Max"},
        )
    else:
        bind.execute(
            text("""
                UPDATE product_listings
                   SET title=:title, price=1299.00, currency='USD',
                       status='published', featured=TRUE, updated_at=NOW()
                 WHERE id=:listing_id
            """),
            {"title": "iPhone 18 Pro Max", "listing_id": listing},
        )

    image_exists = bind.execute(
        text("SELECT 1 FROM product_images WHERE product_id=:product_id LIMIT 1"),
        {"product_id": product_id},
    ).scalar_one_or_none()
    if image_exists is None:
        bind.execute(
            text("""
                INSERT INTO product_images(product_id,image_url,alt_text,sort_order,created_at)
                VALUES(:product_id,:image_url,:alt_text,0,NOW())
            """),
            {
                "product_id": product_id,
                "image_url": IMAGE_URL,
                "alt_text": "Apple iPhone 18 Pro Max",
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    product_id = bind.execute(
        text("SELECT id FROM products WHERE slug=:slug LIMIT 1"),
        {"slug": SLUG},
    ).scalar_one_or_none()
    if product_id is None:
        return
    bind.execute(text("DELETE FROM product_images WHERE product_id=:product_id"), {"product_id": product_id})
    bind.execute(text("DELETE FROM product_listings WHERE product_id=:product_id"), {"product_id": product_id})
    bind.execute(text("DELETE FROM products WHERE id=:product_id"), {"product_id": product_id})
