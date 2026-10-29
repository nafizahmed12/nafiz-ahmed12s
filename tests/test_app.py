import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200


def test_liveness_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_security_headers_are_present():
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_sensitive_pages_are_not_cached():
    response = client.get("/login")
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"


def test_homepage_has_newsroom_navigation_and_latest_news_label():
    response = client.get("/")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Latest in tech" in page
    assert "Reviews" in page
    assert "AI" in page


def test_pages_include_step_by_step_back_navigation():
    response = client.get("/")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="site-back-button"' in page
    assert "history.back()" in page
    assert 'aria-label="Go back to the previous page"' in page
