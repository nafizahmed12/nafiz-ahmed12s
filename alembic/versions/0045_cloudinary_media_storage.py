"""Add Cloudinary storage metadata to editorial media.

Revision ID: 0045_cloudinary_media_storage
Revises: 0044_admin_editorial_tools
"""
from alembic import op
import sqlalchemy as sa

revision = "0045_cloudinary_media_storage"
down_revision = "0044_admin_editorial_tools"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("admin_media")}
    if "storage_provider" not in columns:
        op.add_column(
            "admin_media",
            sa.Column("storage_provider", sa.String(30), nullable=False, server_default="local"),
        )
    if "storage_key" not in columns:
        op.add_column("admin_media", sa.Column("storage_key", sa.String(500), nullable=True))
    if "secure_url" not in columns:
        op.add_column("admin_media", sa.Column("secure_url", sa.String(2048), nullable=True))


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("admin_media")}
    if "secure_url" in columns:
        op.drop_column("admin_media", "secure_url")
    if "storage_key" in columns:
        op.drop_column("admin_media", "storage_key")
    if "storage_provider" in columns:
        op.drop_column("admin_media", "storage_provider")
