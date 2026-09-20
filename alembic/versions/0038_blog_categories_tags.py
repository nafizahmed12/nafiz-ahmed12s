"""Add normalized blog categories and tags.

Revision ID: 0038_blog_categories_tags
Revises: 0037_fix_phone_catalog_images
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0038_blog_categories_tags"
down_revision: Union[str, Sequence[str], None] = "0037_fix_phone_catalog_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("blog_categories"):
        op.create_table(
            "blog_categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False, unique=True),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.String(320), nullable=False, server_default=""),
        )
        op.create_index("ix_blog_categories_slug", "blog_categories", ["slug"], unique=True)

    if not inspector.has_table("blog_tags"):
        op.create_table(
            "blog_tags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False, unique=True),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
        )
        op.create_index("ix_blog_tags_slug", "blog_tags", ["slug"], unique=True)

    if not inspector.has_table("blog_article_tags"):
        op.create_table(
            "blog_article_tags",
            sa.Column("article_id", sa.Integer(), sa.ForeignKey("blog_articles.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("blog_tags.id", ondelete="CASCADE"), primary_key=True),
        )
        op.create_index("ix_blog_article_tags_tag_id", "blog_article_tags", ["tag_id"], unique=False)

    bind.execute(sa.text("""
        INSERT INTO blog_categories (name, slug, description)
        SELECT DISTINCT category,
               lower(trim(replace(replace(category, ' ', '-'), '--', '-'))),
               ''
        FROM blog_articles
        WHERE category IS NOT NULL AND trim(category) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM blog_categories c WHERE c.name = blog_articles.category
          )
    """))


def downgrade() -> None:
    op.drop_table("blog_article_tags")
    op.drop_table("blog_tags")
    op.drop_table("blog_categories")
