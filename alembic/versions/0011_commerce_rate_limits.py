"""Add rate-limit tables for cart, checkout, and payment API routes.

Revision ID: 0011_commerce_rate_limits
Revises: 0010_merge_heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_commerce_rate_limits"
down_revision: Union[str, Sequence[str], None] = "0010_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in _inspector().get_indexes(table))


# Same shape/pattern as the rate-limit tables added in 0001_initial_schema
# (registration_rate_limits, login_rate_limits, contact_rate_limits,
# subscribe_rate_limits) — reused here for the commerce API routes that
# had no rate limiting: cart mutations, checkout creation, and payment
# attempt creation.
_RATE_LIMIT_TABLES = (
    "cart_rate_limits",
    "checkout_rate_limits",
    "payment_rate_limits",
)


def upgrade() -> None:
    for table_name in _RATE_LIMIT_TABLES:
        if not _table_exists(table_name):
            op.create_table(
                table_name,
                sa.Column("rate_key", sa.String(length=255), nullable=False),
                sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
                sa.PrimaryKeyConstraint("rate_key"),
            )
        if _table_exists(table_name) and not _index_exists(table_name, f"ix_{table_name}_window"):
            op.create_index(f"ix_{table_name}_window", table_name, ["window_started_at"], unique=False)


def downgrade() -> None:
    # Baseline migrations should not destroy production data during rollback
    # (see docs/DATABASE_BACKUPS.md). Dropping empty rate-limit tables is
    # safe since they hold no user data, only counters.
    for table_name in _RATE_LIMIT_TABLES:
        if _table_exists(table_name):
            op.drop_table(table_name)
