"""Merge the blog and Bangladesh catalog migration heads.

Revision ID: 0042_merge_blog_heads
Revises: 0038_blog_categories_tags, 0041_bd_catalog_provenance
"""

revision = "0042_merge_blog_heads"
down_revision = ("0038_blog_categories_tags", "0041_bd_catalog_provenance")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
