"""Fix iPhone 18 Pro Max catalog category and gallery metadata.

Revision ID: 0032_iphone_18pm_gallery
Revises: 0031_iphone_18_pro_max
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0032_iphone_18pm_gallery"
down_revision: Union[str, Sequence[str], None] = "0031_iphone_18_pro_max"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPLE_PRODUCT_SOURCE = "https://www.apple.com/iphone-18-pro/"

def upgrade() -> None:
    connection = op.get_bind()
    product = connection.execute(text("SELECT id FROM products WHERE slug=:slug LIMIT 1"), {"slug": "iphone-18-pro-max"}).scalar_one_or_none()
    if product is None:
        return
    mobile_category = connection.execute(text("SELECT id FROM product_categories WHERE LOWER(slug)=:slug LIMIT 1"), {"slug": "mobile"}).scalar_one_or_none()
    if mobile_category is not None:
        connection.execute(text("UPDATE products SET category_id=:category_id, updated_at=NOW() WHERE id=:id"), {"category_id": mobile_category, "id": product})
    connection.execute(text("DELETE FROM product_images WHERE product_id=:product_id"), {"product_id": product})
    connection.execute(text("INSERT INTO product_images (product_id,image_url,alt_text,sort_order,created_at) VALUES (:product_id,:image_url,:alt_text,0,NOW())"), {"product_id": product, "image_url": APPLE_PRODUCT_SOURCE, "alt_text": "Apple official iPhone 18 Pro Max product imagery source"})

def downgrade() -> None:
    connection = op.get_bind()
    product = connection.execute(text("SELECT id FROM products WHERE slug=:slug LIMIT 1"), {"slug": "iphone-18-pro-max"}).scalar_one_or_none()
    if product is not None:
        connection.execute(text("DELETE FROM product_images WHERE product_id=:product_id"), {"product_id": product})
