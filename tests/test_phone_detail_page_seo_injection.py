"""Regression tests for /phone-detail/<slug> and /shop?category=<x>'s SEO
injection hooks in error_handlers.py.

Both hooks (add_product_page_seo's breadcrumb injection, add_category_seo's
canonical-URL injection) called url_for("shop", _external=True). "shop" was
never a registered Flask endpoint -- shop_routes.py registers it as a
blueprint (`shop_bp = Blueprint("shop_ui", __name__)`), so the real endpoint
name is "shop_ui.shop". Every single call raised
werkzeug.routing.exceptions.BuildError.

Both call sites are wrapped in a broad `except Exception` that only logs
("Product page SEO optimization failed" / a similar message for the
category hook) and returns the page unenhanced, so this was invisible in a
manual browser check: every request still returned a normal-looking 200,
just silently missing its BreadcrumbList schema, canonical tag, and
Open Graph/CollectionPage metadata. tests/test_seo_indexing.py's
PUBLIC_SEO_PATHS list only covers the 5 static iphone-18-* pages (which
don't hit either hook), so this had zero coverage.

Separately, /phone-detail/<slug> itself 500'd on every request (a template
syntax error in templates/product_phone.html, fixed alongside this) --
these tests exercise the route after that fix, since the breadcrumb hook
can't be tested against a page that never successfully renders.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")

from app import app, products

PHONE_DETAIL_SLUGS = tuple(products.keys())


def test_phone_detail_pages_render_successfully():
    """/phone-detail/<slug> must not 500 for any slug in app.py's products
    dict -- these are the exact slugs /sitemap.xml submits to search
    engines (see app.py's sitemap_xml() route).
    """
    app.config.update(TESTING=True)
    with app.test_client() as client:
        for slug in PHONE_DETAIL_SLUGS:
            response = client.get(f"/phone-detail/{slug}")
            assert response.status_code == 200, f"/phone-detail/{slug} returned {response.status_code}"


def test_phone_detail_pages_get_breadcrumb_schema_and_robots_meta():
    """error_handlers.py's add_product_page_seo() after_request hook must
    successfully inject a BreadcrumbList schema (via a working url_for
    call) into every /phone-detail/<slug> response.
    """
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get(f"/phone-detail/{PHONE_DETAIL_SLUGS[0]}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

    assert "BreadcrumbList" in html
    assert 'name="robots"' in html


def test_shop_category_pages_get_canonical_and_collection_schema():
    """/shop?category=<known category> must get its canonical URL,
    CollectionPage schema, and category-specific title -- all of which
    depend on add_category_seo()'s url_for("shop_ui.shop", ...) call
    succeeding.
    """
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/shop?category=fashion")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

    assert "<title>Shop Fashion Products in Bangladesh | Nafiz Ecommerce</title>" in html
    assert "CollectionPage" in html
    assert 'href="http://localhost/shop?category=fashion"' in html
