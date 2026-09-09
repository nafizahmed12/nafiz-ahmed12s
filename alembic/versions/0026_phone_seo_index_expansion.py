"""Add no schema changes; marker for phone SEO index expansion."""
from alembic import op

revision = "0026_phone_seo_index_expansion"
down_revision = "0025_verified_phone_expansion_20"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
