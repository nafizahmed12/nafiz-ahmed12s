"""Add supplier fulfillment workflow for dropshipping orders.

Revision ID: 0007_supplier_fulfillment
Revises: 0006_customer_commerce_api
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007_supplier_fulfillment"
down_revision: Union[str, Sequence[str], None] = "0006_customer_commerce_api"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in sa.inspect(op.get_bind()).get_indexes(table))


def _index(name: str, table: str, columns: list[str], unique: bool = False) -> None:
    if _table_exists(table) and not _index_exists(table, name):
        op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    if not _table_exists("supplier_orders"):
        op.create_table(
            "supplier_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier_profiles.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("external_order_ref", sa.String(180), nullable=True),
            sa.Column("tracking_number", sa.String(180), nullable=True),
            sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("cost_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("ix_supplier_orders_order_id", "supplier_orders", ["order_id"])
    _index("ix_supplier_orders_supplier_id", "supplier_orders", ["supplier_id"])
    _index("ix_supplier_orders_status", "supplier_orders", ["status"])
    _index("ix_supplier_orders_external_ref", "supplier_orders", ["external_order_ref"])

    if not _table_exists("supplier_order_items"):
        op.create_table(
            "supplier_order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("supplier_order_id", sa.Integer(), sa.ForeignKey("supplier_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("commerce_order_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("supplier_product_id", sa.Integer(), sa.ForeignKey("supplier_products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("cost_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("line_cost", sa.Numeric(12, 2), nullable=False),
        )
    _index("ix_supplier_order_items_supplier_order", "supplier_order_items", ["supplier_order_id"])
    _index("ix_supplier_order_items_order_item", "supplier_order_items", ["order_item_id"])
    _index("ix_supplier_order_items_supplier_product", "supplier_order_items", ["supplier_product_id"])


def downgrade() -> None:
    pass
