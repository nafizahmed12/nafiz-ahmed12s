"""Add scheduled publication timestamp to blog articles.

Revision ID: 0045_article_scheduling
Revises: 0044_article_seo_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0045_article_scheduling"
down_revision = "0044_article_seo_metadata"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "scheduled_at" not in {c["name"] for c in inspector.get_columns("blog_articles")}:
        op.add_column("blog_articles", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_blog_articles_scheduled_at", "blog_articles", ["scheduled_at"], if_not_exists=True)


def downgrade():
    op.drop_index("ix_blog_articles_scheduled_at", table_name="blog_articles")
    op.drop_column("blog_articles", "scheduled_at")
