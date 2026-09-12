"""Regression tests for /affiliate-picks being server-rendered.

The page previously shipped its entire product grid as client-side-only
JavaScript: view-source showed just <div class="empty">Loading picks...</div>
in the raw HTML, with every product name, description, and Amazon link
injected later by a fetch('/api/affiliate-products') call and no
server-rendered fallback -- unlike every other content page on this site,
which is Jinja-rendered. Flagged during an AdSense-readiness review: this
is the one page on the site most likely to draw scrutiny for thin/
low-value affiliate content, and also the one page whose content a
lightweight crawler might not see at all.

Fixed by having affiliate_picks_page() query affiliate_products directly
(same status='published', sort_order-ordered query commerce_routes.py's
/api/affiliate-products already used) and rendering the grid server-side
via Jinja, matching the pattern every other page on this site already
follows. The client-side fetch()/load() JS is removed entirely -- the
server now sends the full list on first response, so a second client-side
fetch of the same data would be redundant work, not a fallback.

Since affiliate_products only exists via the Postgres-only Alembic
migration chain (not init_db()'s lightweight SQLite bootstrap -- a known,
already-documented gap for several tables in this codebase), these tests
create the table directly via a raw CREATE TABLE, matching the shape
admin_affiliate_routes.py's INSERT/UPDATE statements already assume.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")

import pytest
from sqlalchemy import text

import app as app_module
from database import engine

client = app_module.app.test_client()


@pytest.fixture
def affiliate_products_table():
    """Create a throwaway affiliate_products table for the duration of one
    test, then drop it -- this repo's SQLite test bootstrap doesn't include
    this table (it's Postgres-migration-only), so tests exercising it need
    to stand it up themselves.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS affiliate_products (
                id INTEGER PRIMARY KEY,
                name TEXT, description TEXT, amazon_url TEXT,
                image_url TEXT, display_price TEXT,
                status TEXT, sort_order INTEGER DEFAULT 0
            )
        """))
    yield
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS affiliate_products"))


def _insert(name, description, amazon_url, status, sort_order, image_url=None, display_price=None):
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO affiliate_products
                (name, description, amazon_url, image_url, display_price, status, sort_order)
                VALUES (:name, :description, :amazon_url, :image_url, :display_price, :status, :sort_order)"""),
            {
                "name": name, "description": description, "amazon_url": amazon_url,
                "image_url": image_url, "display_price": display_price,
                "status": status, "sort_order": sort_order,
            },
        )


def test_affiliate_picks_has_no_leftover_client_side_fetch_or_loading_state():
    """The page must not ship the old fetch()/load() JS or the perpetual
    'Loading picks...' placeholder -- those are exactly what made the
    product grid invisible in view-source before this fix.
    """
    response = client.get("/affiliate-picks")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Loading picks" not in html
    assert "fetch(" not in html
    assert "/api/affiliate-products" not in html


def test_affiliate_picks_renders_products_directly_in_the_html(affiliate_products_table):
    """A published product's name, description, price, and Amazon link must
    appear directly in the server's HTML response -- no JS execution
    required to see them, which is the whole point of this fix.
    """
    _insert(
        name="Anker 20W Charger",
        description="Fast, small, and reliable -- this is what we actually use daily.",
        amazon_url="https://amazon.com/test-product",
        status="published", sort_order=1,
        image_url="https://example.com/img.jpg", display_price="\u09f31,200",
    )

    response = client.get("/affiliate-picks")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Anker 20W Charger" in html
    assert "Fast, small, and reliable" in html
    assert "\u09f31,200" in html
    assert 'href="https://amazon.com/test-product"' in html
    assert 'rel="noopener noreferrer sponsored"' in html


def test_affiliate_picks_excludes_draft_products(affiliate_products_table):
    """Only status='published' rows should ever reach the page -- draft
    items must not leak into the public HTML.
    """
    _insert(name="Published Item", description="x", amazon_url="https://amazon.com/a", status="published", sort_order=1)
    _insert(name="Draft Item", description="x", amazon_url="https://amazon.com/b", status="draft", sort_order=2)

    html = client.get("/affiliate-picks").get_data(as_text=True)
    assert "Published Item" in html
    assert "Draft Item" not in html


def test_affiliate_picks_orders_by_sort_order_then_id_desc(affiliate_products_table):
    """Must match the exact ordering commerce_routes.py's
    /api/affiliate-products used (sort_order ASC, id DESC) -- an admin
    reordering picks via sort_order should see the same order here.
    """
    _insert(name="Third", description="x", amazon_url="https://amazon.com/3", status="published", sort_order=3)
    _insert(name="First", description="x", amazon_url="https://amazon.com/1", status="published", sort_order=1)
    _insert(name="Second", description="x", amazon_url="https://amazon.com/2", status="published", sort_order=2)

    html = client.get("/affiliate-picks").get_data(as_text=True)
    assert html.index("First") < html.index("Second") < html.index("Third")


def test_affiliate_picks_escapes_product_content():
    """Product name/description come from the admin panel -- they must be
    HTML-escaped, not injected raw, the same protection the old
    client-side esc() helper existed to provide.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS affiliate_products (
                id INTEGER PRIMARY KEY,
                name TEXT, description TEXT, amazon_url TEXT,
                image_url TEXT, display_price TEXT,
                status TEXT, sort_order INTEGER DEFAULT 0
            )
        """))
    try:
        _insert(
            name="<script>alert(1)</script>",
            description='test"><img src=x onerror=alert(2)>',
            amazon_url="https://amazon.com/xss-test",
            status="published", sort_order=0,
        )
        html = client.get("/affiliate-picks").get_data(as_text=True)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert "<img src=x onerror=alert(2)>" not in html
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS affiliate_products"))


def test_affiliate_picks_shows_empty_state_with_no_published_products(affiliate_products_table):
    """An empty (but existing) table must show the friendly empty-state
    message, not a blank grid or an error.
    """
    html = client.get("/affiliate-picks").get_data(as_text=True)
    assert "No affiliate picks yet" in html


def test_affiliate_picks_survives_a_missing_table_without_crashing():
    """If affiliate_products doesn't exist at all (this repo's own SQLite
    test bootstrap, and this exact test's own baseline state -- no
    fixture creates the table here), the page must still return 200 with
    a graceful message, matching the old client-side catch(e) fallback,
    not a 500.
    """
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS affiliate_products"))
    response = client.get("/affiliate-picks")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Could not load affiliate picks" in html
