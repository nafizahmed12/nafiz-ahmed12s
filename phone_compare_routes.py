"""Indexable phone comparison hub for internal linking and discovery."""

from itertools import combinations

from flask import Blueprint, render_template
from sqlalchemy import text

from database import SessionLocal


phone_compare_bp = Blueprint("phone_compare_hub", __name__)


@phone_compare_bp.get("/compare")
def compare_hub():
    """Show curated comparison pairs built from published phone records."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """SELECT brand, model, slug, short_description, price_usd, price_bdt, published_at
                FROM phone_catalog
                WHERE status='published'
                ORDER BY published_at DESC NULLS LAST, id DESC
                LIMIT 14"""
            )
        ).mappings().all()

    phones = [dict(row) for row in rows]
    comparisons = []
    for left, right in combinations(phones, 2):
        comparisons.append(
            {
                "left": left,
                "right": right,
                "url_slug": f"{left['slug']}-vs-{right['slug']}",
            }
        )

    return render_template("phone_compare_hub.html", phones=phones, comparisons=comparisons[:40])


def register_phone_compare_routes(app):
    app.register_blueprint(phone_compare_bp)
