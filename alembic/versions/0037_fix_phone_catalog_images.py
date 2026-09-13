"""Give phone catalog rows with missing images distinct model artwork.

Revision ID: 0037_fix_phone_catalog_images
Revises: 0036_seed_editorial_blog
"""
from alembic import op
from sqlalchemy import text

revision = "0037_fix_phone_catalog_images"
down_revision = "0036_seed_editorial_blog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("""
        UPDATE phone_catalog
        SET image_url = 'data:image/svg+xml;base64,' || encode(
            convert_to(
                format(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000" viewBox="0 0 800 1000">'
                    || '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111827"/><stop offset="1" stop-color="#334155"/></linearGradient></defs>'
                    || '<rect width="800" height="1000" rx="64" fill="#f1f5f9"/>'
                    || '<rect x="205" y="80" width="390" height="760" rx="52" fill="url(#g)"/>'
                    || '<rect x="225" y="115" width="350" height="690" rx="38" fill="#0f172a"/>'
                    || '<circle cx="400" cy="760" r="7" fill="#64748b"/>'
                    || '<rect x="275" y="180" width="250" height="18" rx="9" fill="#64748b" opacity=".75"/>'
                    || '<text x="400" y="420" text-anchor="middle" font-family="Arial,sans-serif" font-size="34" font-weight="700" fill="#e2e8f0">%s</text>'
                    || '<text x="400" y="470" text-anchor="middle" font-family="Arial,sans-serif" font-size="25" fill="#94a3b8">%s</text>'
                    || '<text x="400" y="900" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" font-weight="700" fill="#475569">Phone catalog artwork</text>'
                    || '</svg>',
                    replace(replace(replace(brand, '&', '&amp;'), '<', '&lt;'), '>', '&gt;'),
                    replace(replace(replace(model, '&', '&amp;'), '<', '&lt;'), '>', '&gt;')
                ),
                'UTF8'
            ),
            'base64'
        )
        WHERE status = 'published' AND (image_url IS NULL OR btrim(image_url) = '')
    """))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("""
        UPDATE phone_catalog
        SET image_url = NULL
        WHERE status = 'published'
          AND image_url LIKE 'data:image/svg+xml;base64,%'
    """))
