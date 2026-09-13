"""Fix provenance metadata for the September 2026 BD catalog refresh.

0040 mixed official, unofficial, reference, and expected prices but stored every
row as ``verified``. This migration deliberately downgrades the mixed refresh to
``reference`` unless the source status is independently re-established later.
It also repairs the known Tecno slug typo from 0040 when that published row exists.
"""
from alembic import op
from sqlalchemy import text

revision = "0041_bd_catalog_provenance"
down_revision = "0040_bd_catalog_refresh"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # 0040 used a mixed source set but labelled all refreshed prices verified.
    # Keep the safer interpretation until each individual model has a directly
    # verified Bangladesh listing.
    bind.execute(text("""
        UPDATE phone_catalog
        SET data_confidence = 'reference',
            source_name = 'GSMArena Bangladesh / current BD reference (status mixed)',
            source_url = 'https://www.gsmarena.com.bd/top-phones',
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'published'
          AND source_checked_at::date = DATE '2026-09-13'
          AND source_name = 'GSMArena Bangladesh / current BD reference'
    """))

    # 0040 accidentally used a Cyrillic 'с' in this slug. Repair the price row
    # only when the real published catalog slug exists.
    bind.execute(text("""
        UPDATE phone_catalog
        SET price_bdt = 24999,
            data_confidence = 'verified',
            source_name = 'GSMArena Bangladesh / current BD reference',
            source_url = 'https://www.gsmarena.com.bd/top-phones',
            source_checked_at = TIMESTAMP '2026-09-13 00:00:00',
            updated_at = CURRENT_TIMESTAMP
        WHERE slug = 'tecno-spark-40-pro-plus'
          AND status = 'published'
    """))


def downgrade():
    # Do not restore the incorrect 0040-wide verified claim on downgrade.
    pass
