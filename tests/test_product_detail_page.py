import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def test_product_detail_page_renders_with_correct_id():
    """/product/<int> must exist and pass the real numeric id to the template.

    Regression: this route was silently dropped from app.py after PR #23,
    while templates/product.html and its backing /api/products/<id> +
    /api/products/<id>/reviews endpoints stayed intact, and shop.html's
    product cards kept linking to it — every card click 404'd.
    """
    response = client.get("/product/7")
    assert response.status_code == 200
    assert b"const productId=7;" in response.data


def test_product_detail_page_only_matches_integer_ids():
    """A non-numeric path must 404 here, not fall through to /phone-detail's
    string-slug route — the two are separate concepts (real commerce
    products vs. the static phone catalog) and must stay disambiguated.
    """
    response = client.get("/product/some-slug")
    assert response.status_code == 404
