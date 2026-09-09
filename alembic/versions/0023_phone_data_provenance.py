"""Add source provenance fields to phone catalog.

Revision ID: 0023_phone_data_provenance
Revises: 0022_seed_phone_catalog
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_phone_data_provenance"
down_revision = "0022_seed_phone_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("phone_catalog", sa.Column("source_name", sa.String(120), nullable=True))
    op.add_column("phone_catalog", sa.Column("source_url", sa.String(2048), nullable=True))
    op.add_column("phone_catalog", sa.Column("source_checked_at", sa.DateTime(), nullable=True))
    op.add_column("phone_catalog", sa.Column("data_confidence", sa.String(20), nullable=False, server_default="unverified"))


def downgrade():
    op.drop_column("phone_catalog", "data_confidence")
    op.drop_column("phone_catalog", "source_checked_at")
    op.drop_column("phone_catalog", "source_url")
    op.drop_column("phone_catalog", "source_name")
