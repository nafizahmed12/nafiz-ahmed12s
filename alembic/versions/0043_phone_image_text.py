"""Allow larger uploaded phone catalog images stored as data URLs.

Revision ID: 0043_phone_image_text
Revises: 0042_merge_blog_heads
"""
from alembic import op
import sqlalchemy as sa

revision = "0043_phone_image_text"
down_revision = "0042_merge_blog_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "phone_catalog",
        "image_url",
        existing_type=sa.String(length=2048),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    # Keep TEXT: uploaded data URLs may exceed VARCHAR(2048), so narrowing
    # would risk truncating or rejecting existing image data.
    pass
