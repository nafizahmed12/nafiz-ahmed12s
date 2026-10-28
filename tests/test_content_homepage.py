from datetime import datetime, timezone

import app as app_module
from wsgi import app


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement):
        assert "FROM blog_articles" in str(statement)
        assert "status = 'published'" in str(statement)
        return _FakeMappings(self._rows)


def _article(**overrides):
    article = {
        "id": 1,
        "title": "How to Compare Smartphone Cameras",
        "slug": "compare-smartphone-cameras",
        "excerpt": "Understand the camera specifications that matter in everyday use.",
        "category": "Buying Guides",
        "featured_image_url": None,
        "published_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
    }
    article.update(overrides)
    return article


def test_homepage_is_a_global_technology_publication_not_a_storefront(monkeypatch):
    monkeypatch.setattr(app_module, "SessionLocal", lambda: _FakeSession([]))
    response = app.test_client().get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "NafizTech" in body
    assert "Nafiz E-commerce" not in body
    assert "Artificial intelligence (AI)" in body
    assert "Technology," in body
    assert "clearly explained." in body
    assert "Latest articles" in body
    assert 'href="/blog"' in body
    assert "global technology content publication" in body.lower()
    assert "Trusted marketplace" not in body
    assert "Search product" not in body
    assert "Sign In" not in body


def test_homepage_renders_recent_published_article(monkeypatch):
    article = _article()
    monkeypatch.setattr(app_module, "SessionLocal", lambda: _FakeSession([article]))
    response = app.test_client().get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert article["title"] in body
    assert article["excerpt"] in body
    assert "/blog/compare-smartphone-cameras" in body
    assert "01 Oct 2026" in body
    assert "Fresh perspectives are on the way." not in body


def test_homepage_has_helpful_empty_state_when_no_articles_are_published(monkeypatch):
    monkeypatch.setattr(app_module, "SessionLocal", lambda: _FakeSession([]))
    response = app.test_client().get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Fresh perspectives are on the way." in body
    assert "Visit article library" in body


def test_homepage_stays_available_when_database_is_unreachable(monkeypatch):
    def unavailable_session():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(app_module, "SessionLocal", unavailable_session)
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Technology," in response.data
    assert b"Fresh perspectives are on the way." in response.data


def test_homepage_has_nafiztech_brand_and_search_metadata(monkeypatch):
    monkeypatch.setattr(app_module, "SessionLocal", lambda: _FakeSession([]))
    response = app.test_client().get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "<title>NafizTech | Mobile, Gadgets, AI and Technology News</title>" in body
    assert 'property="og:site_name" content="NafizTech"' in body
    assert 'name="description" content="NafizTech covers mobile technology, gadgets, artificial intelligence, and technology news for readers worldwide."' in body
    assert 'rel="icon"' in body
