import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")

from datetime import datetime, timezone  # noqa: E402

from sqlalchemy import (  # noqa: E402
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)

import app  # noqa: E402  (registers home_bp's after_app_request hooks via admin_security.py)
from database import SessionLocal, engine  # noqa: E402

client = app.app.test_client()


# home_routes.py's add_home_affiliate_products() (an after_app_request hook)
# injects a "Recommended Accessories" section into every "/" response by
# string-replacing "</main>" in the already-rendered HTML. It queries the
# affiliate_products table directly and, for any row with a non-empty
# image_url, rendered a raw <img src="{image_url}"> pointing at an
# external (e.g. m.media-amazon.com) URL.
#
# On the live homepage this showed a single affiliate product's photo
# stretched across most of the viewport, since .home-affiliate-image sizes
# to its content rather than the reverse. The fix makes image_html always
# render the same text-only ".home-affiliate-no-image" placeholder that
# already existed as the *no-image* fallback, regardless of whether
# image_url is set -- keeping the section, product name, description, and
# "Check on Amazon" link intact, with no <img> tag anywhere in the section.
#
# affiliate_products only exists via the Postgres-only Alembic migration
# chain (see alembic/versions/0019_affiliate_products.py), not the
# lightweight SQLite bootstrap used for local dev (see database.py /
# init_db()). This creates that exact table shape directly so a real
# request can be driven through the full after_app_request hook, rather
# than only pinning source text.
#
# This suite runs against SQLite locally but against real PostgreSQL in
# CI (see .github/workflows/ci.yml's postgres:16 service). The table is
# therefore built with SQLAlchemy's Table/Column API (mirroring the
# columns in the Alembic migration) instead of a raw CREATE TABLE
# string: a literal "DATETIME" column type is valid SQLite but is not a
# PostgreSQL type name (psycopg2.errors.UndefinedObject), so it has to
# go through DateTime() to compile to the right type on each backend.

_metadata = MetaData()
_affiliate_products = Table(
    "affiliate_products",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("amazon_url", String(2048), nullable=False),
    Column("image_url", String(2048), nullable=True),
    Column("display_price", String(50), nullable=True),
    Column("sort_order", Integer, nullable=False, server_default="0"),
    Column("status", String(20), nullable=False, server_default="published"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def _reset_table_with_one_published_row(image_url):
    now = datetime.now(timezone.utc)
    _affiliate_products.create(bind=engine, checkfirst=True)
    with SessionLocal() as db:
        db.execute(text("DELETE FROM affiliate_products"))
        db.execute(
            text(
                """
                INSERT INTO affiliate_products
                    (id, name, description, amazon_url, image_url, display_price,
                     sort_order, status, created_at, updated_at)
                VALUES
                    (:id, :name, :description, :amazon_url, :image_url, :display_price,
                     0, 'published', :created_at, :updated_at)
                """
            ),
            {
                "id": 1,
                "name": "iphone 17 pro max",
                "description": "Premium accessory for Iphone 17 Pro Max.",
                "amazon_url": "https://amzn.to/4gyxy5Z",
                "image_url": image_url,
                "display_price": "$24.99",
                "created_at": now,
                "updated_at": now,
            },
        )
        db.commit()


def _drop_table():
    _affiliate_products.drop(bind=engine, checkfirst=True)


def test_home_affiliate_section_never_renders_an_img_tag_even_with_image_url_set():
    _reset_table_with_one_published_row(
        image_url="https://m.media-amazon.com/images/I/51GOhI8bhHL._AC_SL1000_.jpg"
    )
    try:
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)

        assert "home-affiliate-section" in body, "affiliate section should still be present"
        assert "<img" not in body, "no <img> tag should render anywhere on the homepage"
        assert "m.media-amazon.com" not in body, "the external image URL should not leak into the page at all"
        assert '<div class="home-affiliate-no-image">Amazon</div>' in body, (
            "the existing text-only placeholder should render instead of an <img> tag"
        )
    finally:
        _drop_table()


def test_home_affiliate_section_keeps_name_description_and_amazon_link():
    _reset_table_with_one_published_row(
        image_url="https://m.media-amazon.com/images/I/51GOhI8bhHL._AC_SL1000_.jpg"
    )
    try:
        resp = client.get("/")
        body = resp.get_data(as_text=True)

        assert "Recommended Accessories" in body
        assert "iphone 17 pro max" in body
        assert "Premium accessory for Iphone 17 Pro Max." in body
        assert re.search(r'href="https://amzn\.to/4gyxy5Z"[^>]*>Check on Amazon', body), (
            "the Amazon affiliate link and its text should be unaffected by the image removal"
        )
        assert "As an Amazon Associate" in body
    finally:
        _drop_table()


def test_home_affiliate_section_renders_no_image_placeholder_when_image_url_is_already_empty():
    # Confirms the pre-existing no-image branch (empty image_url) still
    # renders the same placeholder -- i.e. the fix didn't just move the
    # <img> tag behind a different condition.
    _reset_table_with_one_published_row(image_url=None)
    try:
        resp = client.get("/")
        body = resp.get_data(as_text=True)

        assert "<img" not in body
        assert '<div class="home-affiliate-no-image">Amazon</div>' in body
    finally:
        _drop_table()
