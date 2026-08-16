"""Create the initial application schema.

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


def upgrade() -> None:
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
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

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
    op.create_index("ix_websites_owner_id", "websites", ["owner_id"], unique=False)
    op.create_index("ix_websites_slug", "websites", ["slug"], unique=False)
    op.create_index(
        "ix_websites_owner_id_id_desc",
        "websites",
        ["owner_id", sa.text("id DESC")],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_subscribers_email", "subscribers", ["email"], unique=False)

    for table_name in (
        "registration_rate_limits",
        "login_rate_limits",
        "contact_rate_limits",
        "subscribe_rate_limits",
    ):
        op.create_table(
            table_name,
            sa.Column("rate_key", sa.String(length=255), nullable=False),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("rate_key"),
        )
        op.create_index(
            f"ix_{table_name}_window",
            table_name,
            ["window_started_at"],
            unique=False,
        )


def downgrade() -> None:
    for table_name in (
        "subscribe_rate_limits",
        "contact_rate_limits",
        "login_rate_limits",
        "registration_rate_limits",
    ):
        op.drop_index(f"ix_{table_name}_window", table_name=table_name)
        op.drop_table(table_name)

    op.drop_index("ix_subscribers_email", table_name="subscribers")
    op.drop_table("subscribers")
    op.drop_table("messages")

    op.drop_index("ix_websites_owner_id_id_desc", table_name="websites")
    op.drop_index("ix_websites_slug", table_name="websites")
    op.drop_index("ix_websites_owner_id", table_name="websites")
    op.drop_table("websites")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
