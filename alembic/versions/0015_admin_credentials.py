"""Create the admin credentials table used by the admin login flow.

Revision ID: 0015_admin_credentials
Revises: 0014_payment_state_machine
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0015_admin_credentials"
down_revision: Union[str, Sequence[str], None] = "0014_payment_state_machine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_credentials (
            id INTEGER PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            password_changed_at TIMESTAMP WITH TIME ZONE NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_credentials")
