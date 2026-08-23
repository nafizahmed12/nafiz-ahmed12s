"""Merge the password-reset branch with the commerce rate-limit branch.

Revision ID: 0012_merge_password_reset_and_commerce
Revises: 0009_password_reset, 0011_commerce_rate_limits

The password-reset migration was introduced on a parallel Alembic branch after
0011 had already been created. This explicit merge keeps a single canonical
Alembic head so `alembic upgrade head` remains deterministic in CI and on
production deployments.
"""
from typing import Sequence, Union

revision: str = "0012_merge_password_reset_and_commerce"
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
