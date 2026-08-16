"""Add digital product delivery and affiliate tracking foundation.

Revision ID: 0008_digital_affiliate_platform
Revises: 0007_supplier_fulfillment
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0008_digital_affiliate"
down_revision: Union[str, Sequence[str], None] = "0007_supplier_fulfillment"
branch_labels = None
depends_on = None


def _exists(name):
    return sa.inspect(op.get_bind()).has_table(name)


def _index(table, name, cols, unique=False):
    if _exists(table):
        indexes = sa.inspect(op.get_bind()).get_indexes(table)
        if not any(i.get("name") == name for i in indexes):
            op.create_index(name, table, cols, unique=unique)


def upgrade():
    if not _exists("digital_products"):
        op.create_table(
            "digital_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("delivery_url", sa.String(1000), nullable=True),
            sa.Column("file_name", sa.String(255), nullable=True),
            sa.Column("version", sa.String(80), nullable=False, server_default="1.0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("digital_products", "ix_digital_products_owner", ["owner_user_id"])

    if not _exists("digital_purchases"):
        op.create_table(
            "digital_purchases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("access_token", sa.String(128), nullable=False, unique=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_download_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("digital_purchases", "ix_digital_purchases_user", ["user_id"])
    _index("digital_purchases", "ix_digital_purchases_product", ["product_id"])
    _index("digital_purchases", "ix_digital_purchases_order", ["order_id"])

    if not _exists("affiliate_profiles"):
        op.create_table(
            "affiliate_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("code", sa.String(40), nullable=False, unique=True),
            sa.Column("commission_rate", sa.Numeric(6, 3), nullable=False, server_default="10"),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("affiliate_profiles", "ix_affiliate_profiles_code", ["code"], unique=True)

    if not _exists("affiliate_clicks"):
        op.create_table(
            "affiliate_clicks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("affiliate_id", sa.Integer(), sa.ForeignKey("affiliate_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("visitor_key", sa.String(128), nullable=True),
            sa.Column("ip_hash", sa.String(128), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("affiliate_clicks", "ix_affiliate_clicks_affiliate", ["affiliate_id"])
    _index("affiliate_clicks", "ix_affiliate_clicks_product", ["product_id"])

    if not _exists("affiliate_conversions"):
        op.create_table(
            "affiliate_conversions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("affiliate_id", sa.Integer(), sa.ForeignKey("affiliate_profiles.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("click_id", sa.Integer(), sa.ForeignKey("affiliate_clicks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("commerce_orders.id", ondelete="RESTRICT"), nullable=False, unique=True),
            sa.Column("order_total", sa.Numeric(12, 2), nullable=False),
            sa.Column("commission_rate", sa.Numeric(6, 3), nullable=False),
            sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    _index("affiliate_conversions", "ix_affiliate_conversions_affiliate", ["affiliate_id"])
    _index("affiliate_conversions", "ix_affiliate_conversions_status", ["status"])


def downgrade():
    pass
