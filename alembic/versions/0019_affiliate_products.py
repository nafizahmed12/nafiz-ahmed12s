"""Add affiliate_products for Amazon Associates picks.

These are display-only external links — no stock, no cart, no reviews —
so they get their own small table rather than reusing the products/
product_listings machinery built for items sold directly on the site.

Revision ID: 0019_affiliate_products
Revises: 0018_review_rate_limits
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_affiliate_products"
down_revision: Union[str, Sequence[str], None] = "0018_review_rate_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in _inspector().get_indexes(table))


_TABLE_NAME = "affiliate_products"


def upgrade() -> None:
    if not _table_exists(_TABLE_NAME):
        op.create_table(
            _TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            # Full Amazon product/affiliate URL, tag included by the admin.
            sa.Column("amazon_url", sa.String(length=2048), nullable=False),
            sa.Column("image_url", sa.String(length=2048), nullable=True),
            # Display-only price text (e.g. "$24.99") — Amazon's own price
            # is the source of truth and can change any time, so this is
            # never used for any calculation, only shown as a hint.
            sa.Column("display_price", sa.String(length=50), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="published"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if _table_exists(_TABLE_NAME) and not _index_exists(_TABLE_NAME, "ix_affiliate_products_status"):
        op.create_index("ix_affiliate_products_status", _TABLE_NAME, ["status"], unique=False)


def downgrade() -> None:
    if _table_exists(_TABLE_NAME):
        op.drop_table(_TABLE_NAME)
