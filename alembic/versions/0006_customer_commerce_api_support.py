"""Add customer-facing commerce support metadata.

Revision ID: 0006_customer_commerce_api_support
Revises: 0005_checkout_payment_order
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_customer_commerce_api_support"
down_revision: Union[str, Sequence[str], None] = "0005_checkout_payment_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in _inspector().get_indexes(table))


def _create_index_if_missing(index: str, table: str, columns: list[str], unique: bool = False) -> None:
    if _table_exists(table) and not _index_exists(table, index):
        op.create_index(index, table, columns, unique=unique)


def upgrade() -> None:
    if not _table_exists("customer_profiles"):
        op.create_table(
            "customer_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("display_name", sa.String(160), nullable=True),
            sa.Column("phone", sa.String(30), nullable=True),
            sa.Column("preferred_currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id"),
        )
    _create_index_if_missing("ix_customer_profiles_user_id", "customer_profiles", ["user_id"], unique=True)

    if not _table_exists("product_reviews"):
        op.create_table(
            "product_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(180), nullable=True),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_product_reviews_product_id", "product_reviews", ["product_id"])
    _create_index_if_missing("ix_product_reviews_user_id", "product_reviews", ["user_id"])
    _create_index_if_missing("ix_product_reviews_order_id", "product_reviews", ["order_id"])
    _create_index_if_missing("ix_product_reviews_status", "product_reviews", ["status"])


def downgrade() -> None:
    pass
