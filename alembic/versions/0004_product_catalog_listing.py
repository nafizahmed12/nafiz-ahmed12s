"""Add product catalog and marketplace listing metadata.

Revision ID: 0004_product_catalog_listing
Revises: 0003_seller_supplier_roles
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_product_catalog_listing"
down_revision: Union[str, Sequence[str], None] = "0003_seller_supplier_roles"
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
    # Product listing is the customer-facing offer. A product can have many
    # seller/supplier offers without duplicating the canonical product.
    if not _table_exists("product_listings"):
        op.create_table(
            "product_listings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id", ondelete="CASCADE"), nullable=True),
            sa.Column("supplier_product_id", sa.Integer(), sa.ForeignKey("supplier_products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("listing_type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(220), nullable=False),
            sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("compare_at_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_product_listings_product_id", "product_listings", ["product_id"])
    _create_index_if_missing("ix_product_listings_seller_id", "product_listings", ["seller_id"])
    _create_index_if_missing("ix_product_listings_supplier_product_id", "product_listings", ["supplier_product_id"])
    _create_index_if_missing("ix_product_listings_listing_type", "product_listings", ["listing_type"])
    _create_index_if_missing("ix_product_listings_status", "product_listings", ["status"])
    _create_index_if_missing("ix_product_listings_featured", "product_listings", ["featured"])

    if not _table_exists("product_attributes"):
        op.create_table(
            "product_attributes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("attribute_name", sa.String(100), nullable=False),
            sa.Column("attribute_value", sa.String(255), nullable=False),
        )
    _create_index_if_missing("ix_product_attributes_product_id", "product_attributes", ["product_id"])

    if not _table_exists("product_variants"):
        op.create_table(
            "product_variants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sku", sa.String(100), nullable=True),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    _create_index_if_missing("ix_product_variants_product_id", "product_variants", ["product_id"])
    _create_index_if_missing("ix_product_variants_sku", "product_variants", ["sku"])


def downgrade() -> None:
    # Non-destructive while production commerce data is being introduced.
    pass
