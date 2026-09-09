"""Add scalable global phone catalog.

Revision ID: 0021_phone_catalog
Revises: 0020_blog_articles
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_phone_catalog"
down_revision = "0020_blog_articles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "phone_catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brand", sa.String(80), nullable=False),
        sa.Column("model", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False, unique=True),
        sa.Column("short_description", sa.String(320), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("release_date", sa.String(40), nullable=True),
        sa.Column("price_usd", sa.String(40), nullable=True),
        sa.Column("price_bdt", sa.String(40), nullable=True),
        sa.Column("specs_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("seo_description", sa.String(320), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_phone_catalog_brand", "phone_catalog", ["brand"])
    op.create_index("ix_phone_catalog_status", "phone_catalog", ["status"])
    op.create_index("ix_phone_catalog_published_at", "phone_catalog", ["published_at"])


def downgrade():
    op.drop_index("ix_phone_catalog_published_at", table_name="phone_catalog")
    op.drop_index("ix_phone_catalog_status", table_name="phone_catalog")
    op.drop_index("ix_phone_catalog_brand", table_name="phone_catalog")
    op.drop_table("phone_catalog")
