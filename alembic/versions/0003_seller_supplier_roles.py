"""Add seller and supplier profiles for marketplace and dropshipping.

Revision ID: 0003_seller_supplier_roles
Revises: 0002_ecommerce_core
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_seller_supplier_roles"
down_revision: Union[str, Sequence[str], None] = "0002_ecommerce_core"
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
    if not _table_exists("seller_profiles"):
        op.create_table(
            "seller_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("store_name", sa.String(160), nullable=False),
            sa.Column("store_slug", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("commission_rate", sa.Numeric(5, 2), nullable=False, server_default="10"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id"),
            sa.UniqueConstraint("store_slug"),
        )
    _create_index_if_missing("ix_seller_profiles_user_id", "seller_profiles", ["user_id"], unique=True)
    _create_index_if_missing("ix_seller_profiles_store_slug", "seller_profiles", ["store_slug"], unique=True)
    _create_index_if_missing("ix_seller_profiles_status", "seller_profiles", ["status"])

    if not _table_exists("supplier_profiles"):
        op.create_table(
            "supplier_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("company_name", sa.String(180), nullable=False),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("contact_email", sa.String(255), nullable=True),
            sa.Column("contact_phone", sa.String(30), nullable=True),
            sa.Column("country", sa.String(80), nullable=False, server_default="Bangladesh"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("slug"),
        )
    _create_index_if_missing("ix_supplier_profiles_user_id", "supplier_profiles", ["user_id"])
    _create_index_if_missing("ix_supplier_profiles_slug", "supplier_profiles", ["slug"], unique=True)
    _create_index_if_missing("ix_supplier_profiles_status", "supplier_profiles", ["status"])

    if not _table_exists("supplier_products"):
        op.create_table(
            "supplier_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("supplier_sku", sa.String(100), nullable=True),
            sa.Column("cost_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("supplier_currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("supplier_stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fulfillment_time_days", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("supplier_id", "product_id"),
        )
    _create_index_if_missing("ix_supplier_products_supplier_id", "supplier_products", ["supplier_id"])
    _create_index_if_missing("ix_supplier_products_product_id", "supplier_products", ["product_id"])
    _create_index_if_missing("ix_supplier_products_active", "supplier_products", ["is_active"])

    if not _table_exists("product_sellers"):
        op.create_table(
            "product_sellers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("seller_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("seller_stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("seller_id", "product_id"),
        )
    _create_index_if_missing("ix_product_sellers_seller_id", "product_sellers", ["seller_id"])
    _create_index_if_missing("ix_product_sellers_product_id", "product_sellers", ["product_id"])
    _create_index_if_missing("ix_product_sellers_active", "product_sellers", ["is_active"])


def downgrade() -> None:
    # Non-destructive by design while commerce data is being introduced.
    pass
