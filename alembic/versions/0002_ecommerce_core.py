"""Add safe e-commerce core tables.

Revision ID: 0002_ecommerce_core
Revises: 0001_initial_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_ecommerce_core"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
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
    # Category is shared by owned, marketplace, dropship, and digital products.
    if not _table_exists("product_categories"):
        op.create_table(
            "product_categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(140), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("slug"),
        )
    _create_index_if_missing("ix_product_categories_slug", "product_categories", ["slug"])

    # One product table supports all five business models without separate catalogs.
    if not _table_exists("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("product_categories.id"), nullable=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(220), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("product_type", sa.String(30), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("sku", sa.String(80), nullable=True),
            sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("slug"),
        )
    _create_index_if_missing("ix_products_category_id", "products", ["category_id"])
    _create_index_if_missing("ix_products_owner_id", "products", ["owner_id"])
    _create_index_if_missing("ix_products_product_type", "products", ["product_type"])
    _create_index_if_missing("ix_products_status", "products", ["status"])
    _create_index_if_missing("ix_products_sku", "products", ["sku"])

    if not _table_exists("product_images"):
        op.create_table(
            "product_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=False),
            sa.Column("alt_text", sa.String(255), nullable=False, server_default=""),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_product_images_product_id", "product_images", ["product_id"])

    if not _table_exists("addresses"):
        op.create_table(
            "addresses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("full_name", sa.String(160), nullable=False),
            sa.Column("phone", sa.String(30), nullable=False),
            sa.Column("address_line", sa.Text(), nullable=False),
            sa.Column("city", sa.String(100), nullable=False),
            sa.Column("postal_code", sa.String(20), nullable=True),
            sa.Column("country", sa.String(80), nullable=False, server_default="Bangladesh"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_addresses_user_id", "addresses", ["user_id"])

    if not _table_exists("carts"):
        op.create_table(
            "carts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_carts_user_id", "carts", ["user_id"], unique=True)

    if not _table_exists("cart_items"):
        op.create_table(
            "cart_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("cart_id", "product_id"),
        )
    _create_index_if_missing("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    _create_index_if_missing("ix_cart_items_product_id", "cart_items", ["product_id"])

    if not _table_exists("orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("address_id", sa.Integer(), sa.ForeignKey("addresses.id"), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("payment_status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("fulfillment_status", sa.String(30), nullable=False, server_default="unfulfilled"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("shipping_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_orders_user_id", "orders", ["user_id"])
    _create_index_if_missing("ix_orders_status", "orders", ["status"])
    _create_index_if_missing("ix_orders_payment_status", "orders", ["payment_status"])

    if not _table_exists("order_items"):
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("product_name", sa.String(200), nullable=False),
            sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        )
    _create_index_if_missing("ix_order_items_order_id", "order_items", ["order_id"])
    _create_index_if_missing("ix_order_items_product_id", "order_items", ["product_id"])


def downgrade() -> None:
    # Intentionally non-destructive. A later dedicated migration can provide
    # explicit rollback once these tables contain real commerce data.
    pass
