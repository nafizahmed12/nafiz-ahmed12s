"""Add blog articles content management table.

Revision ID: 0020_blog_articles
Revises: 0019_affiliate_products
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_blog_articles"
down_revision: Union[str, Sequence[str], None] = "0019_affiliate_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("blog_articles"):
        return
    op.create_table(
        "blog_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False, unique=True),
        sa.Column("excerpt", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="Technology"),
        sa.Column("featured_image_url", sa.String(length=2048), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_blog_articles_status", "blog_articles", ["status"], unique=False)
    op.create_index("ix_blog_articles_published_at", "blog_articles", ["published_at"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("blog_articles"):
        op.drop_table("blog_articles")
