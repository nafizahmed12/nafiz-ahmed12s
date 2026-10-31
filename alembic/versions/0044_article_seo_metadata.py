"""Add editable SEO and social metadata to editorial articles.

Revision ID: 0044_article_seo_metadata
Revises: 0043_phone_image_text
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0044_article_seo_metadata"
down_revision: Union[str, Sequence[str], None] = "0043_phone_image_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("blog_articles")}
    additions = (
        ("seo_title", sa.String(length=200)),
        ("canonical_url", sa.String(length=2048)),
        ("og_title", sa.String(length=200)),
        ("og_description", sa.String(length=320)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("blog_articles", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("blog_articles")}
    for name in ("og_description", "og_title", "canonical_url", "seo_title"):
        if name in columns:
            op.drop_column("blog_articles", name)
