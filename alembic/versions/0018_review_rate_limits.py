"""Add a rate-limit table for the product review submission API.

Revision ID: 0018_review_rate_limits
Revises: 0017_merge_0016_heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_review_rate_limits"
down_revision: Union[str, Sequence[str], None] = "0017_merge_0016_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in _inspector().get_indexes(table))


# Same shape as the rate-limit tables added in 0011_commerce_rate_limits,
# reused here for the new POST /api/products/<id>/reviews route.
_TABLE_NAME = "review_rate_limits"


def upgrade() -> None:
    if not _table_exists(_TABLE_NAME):
        op.create_table(
            _TABLE_NAME,
            sa.Column("rate_key", sa.String(length=255), nullable=False),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("rate_key"),
        )
    if _table_exists(_TABLE_NAME) and not _index_exists(_TABLE_NAME, f"ix_{_TABLE_NAME}_window"):
        op.create_index(f"ix_{_TABLE_NAME}_window", _TABLE_NAME, ["window_started_at"], unique=False)

    # product_reviews already exists (0006_customer_commerce_api_support) with
    # an index on status alone; the review list/average queries filter on
    # (product_id, status), so add a composite index for that access path.
    if _table_exists("product_reviews") and not _index_exists(
        "product_reviews", "ix_product_reviews_product_id_status"
    ):
        op.create_index(
            "ix_product_reviews_product_id_status",
            "product_reviews",
            ["product_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    if _table_exists("product_reviews") and _index_exists(
        "product_reviews", "ix_product_reviews_product_id_status"
    ):
        op.drop_index("ix_product_reviews_product_id_status", table_name="product_reviews")
    if _table_exists(_TABLE_NAME):
        op.drop_table(_TABLE_NAME)
