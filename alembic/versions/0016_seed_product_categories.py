"""Seed the built-in product categories used by the admin product form.

Revision ID: 0016_seed_product_categories
Revises: 0015_admin_credentials
"""
from typing import Sequence, Union

from alembic import op


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
    # The admin UI submits category slugs. Keep these canonical rows present
    # in every deployment without creating duplicates on repeated migrations.
    for name, slug in CATEGORIES:
        op.execute(
            """
            INSERT INTO product_categories (name, slug, description, created_at)
            VALUES (:name, :slug, '', NOW())
            ON CONFLICT (slug) DO NOTHING
            """,
            {"name": name, "slug": slug},
        )


def downgrade() -> None:
    for _, slug in CATEGORIES:
        op.execute(
            "DELETE FROM product_categories WHERE slug = :slug",
            {"slug": slug},
        )
