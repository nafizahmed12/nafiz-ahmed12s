"""Fix iPhone 18 Pro Max catalog category safely.

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


def upgrade() -> None:
    connection = op.get_bind()
    product = connection.execute(
        text("SELECT id FROM products WHERE slug=:slug LIMIT 1"),
        {"slug": "iphone-18-pro-max"},
    ).scalar_one_or_none()
    if product is None:
        return

    # The storefront filters mobile products by category. Set the category
    # only when a mobile category exists; do not invent a category id.
    mobile_category = connection.execute(
        text("SELECT id FROM product_categories WHERE LOWER(slug)=:slug LIMIT 1"),
        {"slug": "mobile"},
    ).scalar_one_or_none()
    if mobile_category is not None:
        connection.execute(
            text("UPDATE products SET category_id=:category_id, updated_at=NOW() WHERE id=:id"),
            {"category_id": mobile_category, "id": product},
        )


def downgrade() -> None:
    # Do not remove the product category on downgrade; the previous migration
    # did not assign one and this migration must remain non-destructive.
    return
