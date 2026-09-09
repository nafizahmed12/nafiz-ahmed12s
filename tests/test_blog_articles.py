import os

os.environ.setdefault("PUBLIC_BASE_URL", "https://nafiz-ahmed12s.onrender.com")

from wsgi import app  # noqa: E402


def test_blog_index_is_public():
    client = app.test_client()
    response = client.get("/blog")
    assert response.status_code == 200
    assert b"Blog & Articles" in response.data


def test_missing_article_returns_404():
    client = app.test_client()
    response = client.get("/blog/does-not-exist")
    assert response.status_code == 404


def test_sitemap_contains_no_unpublished_blog_urls():
    client = app.test_client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert b"/blog/" not in response.data
