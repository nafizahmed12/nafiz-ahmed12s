import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app

client = app.app.test_client()


def test_shop_redirects_apple_and_phones_to_phone_catalog_like_mobile():
    """Apple Products/Phones nav links must use the real phone catalog, not the
    thin /shop product_categories table which has no phone data of its own."""
    for category in ("mobile", "apple", "phones"):
        response = client.get(f"/shop?category={category}")
        assert response.status_code == 302, (category, response.status_code)
        assert response.headers["Location"] == "/phones", (category, response.headers["Location"])


def test_shop_does_not_redirect_the_new_real_categories():
    """The 9 categories seeded by 0035 must render the storefront template
    normally instead of being swept into the phone-catalog redirect."""
    for category in (
        "tablets", "computers", "gadgets", "appliances",
        "lifestyle", "camera", "audio", "wearables", "offers",
    ):
        response = client.get(f"/shop?category={category}")
        assert response.status_code == 200, (category, response.status_code)
        assert b"Nafiz-Ecommerce" in response.data


def test_shop_new_categories_get_deterministic_seo_titles():
    """Each new category should override the shared <title>, matching the
    existing fashion/clothing/beauty/accessories pattern."""
    expectations = {
        "tablets": b"Shop Tablets in Bangladesh",
        "computers": b"Laptops & Desktops in Bangladesh",
        "offers": b"Exclusive Deals & Offers",
    }
    for category, expected_snippet in expectations.items():
        response = client.get(f"/shop?category={category}")
        assert response.status_code == 200
        assert expected_snippet in response.data, (category, response.data[:400])


def test_shop_new_categories_render_matching_chip_as_active():
    """The chip for the current category should carry the 'active' class so
    the taxonomy shown always matches what /shop is actually filtering by."""
    response = client.get("/shop?category=gadgets")
    assert response.status_code == 200
    assert b'data-cat="gadgets" onclick="setCategory(\'gadgets\')">Gadgets</button>' in response.data
    gadgets_chip_start = response.data.index(b'data-cat="gadgets"')
    preceding = response.data[max(0, gadgets_chip_start - 80):gadgets_chip_start]
    assert b"active" in preceding
