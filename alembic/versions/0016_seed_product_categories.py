"""Seed the built-in product categories used by the admin product form.

Revision ID: 0016_seed_product_categories
Revises: 0015_admin_credentials
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "0016_seed_product_categories"
down_revision: Union[str, Sequence[str], None] = "0015_admin_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = (
    ("Fashion", "fashion"),
    ("Clothing", "clothing"),
    ("Beauty", "beauty"),
    ("Accessories", "accessories"),
)


def upgrade() -> None:
    connection = op.get_bind()
    stmt = text(
        """
        INSERT INTO product_categories (name, slug, description, created_at)
        VALUES (:name, :slug, '', NOW())
        ON CONFLICT (slug) DO NOTHING
        """
    )
    for name, slug in CATEGORIES:
        connection.execute(stmt, {"name": name, "slug": slug})


def downgrade() -> None:
    connection = op.get_bind()
    stmt = text("DELETE FROM product_categories WHERE slug = :slug")
    for _, slug in CATEGORIES:
        connection.execute(stmt, {"slug": slug})
