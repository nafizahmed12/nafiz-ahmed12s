"""Add password change timestamp used to revoke older user sessions.

Revision ID: 0013_password_session_revocation
Revises: 0012_merge_heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_password_session_revocation"
down_revision: Union[str, Sequence[str], None] = "0012_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
