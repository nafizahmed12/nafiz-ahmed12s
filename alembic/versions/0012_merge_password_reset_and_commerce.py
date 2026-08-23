"""Merge the password-reset branch with the commerce rate-limit branch.

Revision ID: 0012_merge_heads
Revises: 0009_password_reset, 0011_commerce_rate_limits

This explicit merge keeps a single canonical Alembic head so
`alembic upgrade head` remains deterministic in CI and production.
The revision id is intentionally <= 32 characters because PostgreSQL's
alembic_version.version_num column is VARCHAR(32).
"""
from typing import Sequence, Union

revision: str = "0012_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0009_password_reset",
    "0011_commerce_rate_limits",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
