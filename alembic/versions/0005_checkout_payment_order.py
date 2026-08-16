"""Add commerce checkout, payment, and order transaction tables.

Revision ID: 0005_checkout_payment_order
Revises: 0004_product_catalog_listing
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_checkout_payment_order"
down_revision: Union[str, Sequence[str], None] = "0004_product_catalog_listing"
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
    # Checkout is a short-lived snapshot between cart and order creation.
    if not _table_exists("checkouts"):
        op.create_table(
            "checkouts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("shipping_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("shipping_address_id", sa.Integer(), sa.ForeignKey("addresses.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_checkouts_user_id", "checkouts", ["user_id"])
    _create_index_if_missing("ix_checkouts_status", "checkouts", ["status"])

    if not _table_exists("checkout_items"):
        op.create_table(
            "checkout_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("checkout_id", sa.Integer(), sa.ForeignKey("checkouts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("listing_id", sa.Integer(), sa.ForeignKey("product_listings.id"), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("line_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        )
    _create_index_if_missing("ix_checkout_items_checkout_id", "checkout_items", ["checkout_id"])
    _create_index_if_missing("ix_checkout_items_product_id", "checkout_items", ["product_id"])

    # Transactional order record. Existing orders table remains untouched.
    if not _table_exists("commerce_orders"):
        op.create_table(
            "commerce_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_number", sa.String(40), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("shipping_address_id", sa.Integer(), sa.ForeignKey("addresses.id"), nullable=True),
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
            sa.UniqueConstraint("order_number"),
        )
    _create_index_if_missing("ix_commerce_orders_user_id", "commerce_orders", ["user_id"])
    _create_index_if_missing("ix_commerce_orders_status", "commerce_orders", ["status"])
    _create_index_if_missing("ix_commerce_orders_payment_status", "commerce_orders", ["payment_status"])
    _create_index_if_missing("ix_commerce_orders_order_number", "commerce_orders", ["order_number"], unique=True)

    if not _table_exists("commerce_order_items"):
        op.create_table(
            "commerce_order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("listing_id", sa.Integer(), sa.ForeignKey("product_listings.id"), nullable=True),
            sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id"), nullable=True),
            sa.Column("supplier_product_id", sa.Integer(), sa.ForeignKey("supplier_products.id"), nullable=True),
            sa.Column("product_name", sa.String(220), nullable=False),
            sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        )
    _create_index_if_missing("ix_commerce_order_items_order_id", "commerce_order_items", ["order_id"])
    _create_index_if_missing("ix_commerce_order_items_product_id", "commerce_order_items", ["product_id"])
    _create_index_if_missing("ix_commerce_order_items_seller_id", "commerce_order_items", ["seller_id"])
    _create_index_if_missing("ix_commerce_order_items_supplier_product_id", "commerce_order_items", ["supplier_product_id"])

    if not _table_exists("payments"):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("transaction_id", sa.String(160), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
            sa.Column("provider_reference", sa.String(180), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("ix_payments_order_id", "payments", ["order_id"])
    _create_index_if_missing("ix_payments_transaction_id", "payments", ["transaction_id"])
    _create_index_if_missing("ix_payments_status", "payments", ["status"])


def downgrade() -> None:
    # Non-destructive during production rollout.
    pass
