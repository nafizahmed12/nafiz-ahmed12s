import os

os.environ.setdefault("PUBLIC_BASE_URL", "https://nafiz-ahmed12s.onrender.com")

from wsgi import app  # noqa: E402


def test_blog_category_page_is_public_and_slugged():
    client = app.test_client()
    response = client.get("/blog/category/buying-guides")
    assert response.status_code == 200
    assert b"Buying Guides" in response.data


def test_blog_tag_page_is_public_and_slugged():
    client = app.test_client()
    response = client.get("/blog/tag/smartphone")
    assert response.status_code == 200
    assert b"smartphone" in response.data.lower()


def test_admin_dashboard_exposes_blog_management():
    client = app.test_client()
    response = client.get("/admin")
    assert response.status_code in {200, 302, 401, 403}
    if response.status_code == 200:
        assert b"Blog" in response.data
