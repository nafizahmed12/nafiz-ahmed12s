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


def test_sitemap_contains_published_blog_urls_only():
    client = app.test_client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert b"/blog/" in response.data
    assert b"/blog/does-not-exist" not in response.data


def test_blog_index_canonical_excludes_tracking_query_parameters():
    client = app.test_client()
    response = client.get("/blog?utm_source=newsletter&ref=campaign")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<link rel="canonical" href="http://localhost/blog">' in body
    assert '<meta property="og:url" content="http://localhost/blog">' in body
    assert "utm_source" not in body
    assert "ref=campaign" not in body
