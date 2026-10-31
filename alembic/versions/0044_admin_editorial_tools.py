"""Add editorial scheduling, media, revisions, activity and site settings.

Revision ID: 0044_admin_editorial_tools
Revises: 0043_phone_image_text
"""
from alembic import op
import sqlalchemy as sa

revision = "0044_admin_editorial_tools"
down_revision = "0043_phone_image_text"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("blog_articles"):
        columns = {column["name"] for column in inspector.get_columns("blog_articles")}
        if "scheduled_at" not in columns:
            op.add_column("blog_articles", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("blog_articles")}
        if "ix_blog_articles_scheduled_at" not in indexes:
            op.create_index("ix_blog_articles_scheduled_at", "blog_articles", ["scheduled_at"])

    if not inspector.has_table("article_revisions"):
        op.create_table(
            "article_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("article_id", sa.Integer(), sa.ForeignKey("blog_articles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("snapshot_json", sa.Text(), nullable=False),
            sa.Column("revision_note", sa.String(200), nullable=False, server_default="Article updated"),
            sa.Column("actor", sa.String(120), nullable=False, server_default="admin"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_article_revisions_article_created", "article_revisions", ["article_id", "created_at"])

    if not inspector.has_table("admin_media"):
        op.create_table(
            "admin_media",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False, unique=True),
            sa.Column("original_name", sa.String(255), nullable=False),
            sa.Column("mime_type", sa.String(80), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("alt_text", sa.String(300), nullable=False, server_default=""),
            sa.Column("uploaded_by", sa.String(120), nullable=False, server_default="admin"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_admin_media_created_at", "admin_media", ["created_at"])

    if not inspector.has_table("admin_activity_log"):
        op.create_table(
            "admin_activity_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor", sa.String(120), nullable=False),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("summary", sa.String(500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_admin_activity_created_at", "admin_activity_log", ["created_at"])
        op.create_index("ix_admin_activity_action", "admin_activity_log", ["action"])

    if not inspector.has_table("site_settings"):
        op.create_table(
            "site_settings",
            sa.Column("setting_key", sa.String(80), primary_key=True),
            sa.Column("setting_value", sa.String(1000), nullable=False, server_default=""),
            sa.Column("updated_by", sa.String(120), nullable=False, server_default="admin"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in ("site_settings", "admin_activity_log", "admin_media", "article_revisions"):
        if inspector.has_table(table):
            op.drop_table(table)
    if inspector.has_table("blog_articles"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("blog_articles")}
        if "scheduled_at" in columns:
            op.drop_index("ix_blog_articles_scheduled_at", table_name="blog_articles")
            op.drop_column("blog_articles", "scheduled_at")
