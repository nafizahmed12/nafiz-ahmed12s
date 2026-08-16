"""Baseline the existing application schema safely.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, index: str) -> bool:
    return any(i.get("name") == index for i in _inspector().get_indexes(table))


def upgrade() -> None:
    # This is a baseline migration for an already-running application.
    # Existing tables are preserved; only missing objects are created.
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("username"),
        )
    if _table_exists("users"):
        if not _index_exists("users", "ix_users_username"):
            op.create_index("ix_users_username", "users", ["username"], unique=False)
        if not _index_exists("users", "ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"], unique=False)

    if not _table_exists("websites"):
        op.create_table(
            "websites",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("slug", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
    if _table_exists("websites"):
        if not _index_exists("websites", "ix_websites_owner_id"):
            op.create_index("ix_websites_owner_id", "websites", ["owner_id"], unique=False)
        if not _index_exists("websites", "ix_websites_slug"):
            op.create_index("ix_websites_slug", "websites", ["slug"], unique=False)

    if not _table_exists("messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("subscribers"):
        op.create_table(
            "subscribers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
    if _table_exists("subscribers") and not _index_exists("subscribers", "ix_subscribers_email"):
        op.create_index("ix_subscribers_email", "subscribers", ["email"], unique=False)

    for table_name in (
        "registration_rate_limits",
        "login_rate_limits",
        "contact_rate_limits",
        "subscribe_rate_limits",
    ):
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
    # Baseline migrations should not destroy production data during rollback.
    # Future schema changes should have their own reversible migrations.
    pass
