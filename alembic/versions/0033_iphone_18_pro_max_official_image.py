"""Use the official Apple iPhone 18 Pro Max storefront image.

Revision ID: 0033_iphone_18pm_official_image
Revises: 0032_iphone_18pm_gallery
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0033_iphone_18pm_official_image"
down_revision: Union[str, Sequence[str], None] = "0032_iphone_18pm_gallery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OFFICIAL_IMAGE = "/static/images/iphone-18-pro-max-official.jpg"


def upgrade() -> None:
    connection = op.get_bind()
    product_id = connection.execute(
        text("SELECT id FROM products WHERE slug=:slug LIMIT 1"),
        {"slug": "iphone-18-pro-max"},
    ).scalar_one_or_none()
    if product_id is None:
        return

    image_id = connection.execute(
        text(
            "SELECT id FROM product_images "
            "WHERE product_id=:product_id ORDER BY sort_order ASC, id ASC LIMIT 1"
        ),
        {"product_id": product_id},
    ).scalar_one_or_none()

    if image_id is not None:
        connection.execute(
            text(
                "UPDATE product_images SET image_url=:image_url, "
                "alt_text=:alt_text WHERE id=:id"
            ),
            {
                "image_url": OFFICIAL_IMAGE,
                "alt_text": "iPhone 18 Pro Max in Burgundy, official Apple product image",
                "id": image_id,
            },
        )
    else:
        connection.execute(
            text(
                "INSERT INTO product_images "
                "(product_id,image_url,alt_text,sort_order,created_at) "
                "VALUES(:product_id,:image_url,:alt_text,0,NOW())"
            ),
            {
                "product_id": product_id,
                "image_url": OFFICIAL_IMAGE,
                "alt_text": "iPhone 18 Pro Max in Burgundy, official Apple product image",
            },
        )


def downgrade() -> None:
    return
