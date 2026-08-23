import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app

client = app.app.test_client()


def test_production_public_routes():
    for path in ("/", "/robots.txt", "/sitemap.xml", "/health", "/login", "/user-login", "/register", "/shop"):
        response = client.get(path)
        assert response.status_code < 500, (path, response.status_code)


def test_not_found_handler():
    response = client.get("/definitely-not-a-real-route")
    assert response.status_code == 404


def test_sensitive_routes_require_authentication():
    for path in ("/dashboard", "/account", "/orders", "/admin"):
        response = client.get(path)
        assert response.status_code in (302, 401, 403), (path, response.status_code)


def test_admin_login_initializes_privileged_session():
    response = client.post(
        "/login",
        data={"username": "ci-admin", "password": "ci-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")

    with client.session_transaction() as session:
        assert session.get("admin_logged_in") is True
        assert session.get("admin_authenticated_at") is not None
        assert session.get("admin_last_activity") is not None

    client.get("/logout", follow_redirects=False)


def test_admin_login_rejects_invalid_credentials():
    response = client.post(
        "/login",
        data={"username": "ci-admin", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 401

    with client.session_transaction() as session:
        assert not session.get("admin_logged_in")


def test_admin_logout_clears_privileged_session():
    response = client.post(
        "/login",
        data={"username": "ci-admin", "password": "ci-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert not session.get("admin_logged_in")
        assert session.get("admin_authenticated_at") is None
        assert session.get("admin_last_activity") is None


def test_admin_login_rate_limit_is_enforced():
    for _ in range(5):
        response = client.post(
            "/login",
            data={"username": "rate-limit-test", "password": "wrong-password"},
            follow_redirects=False,
        )
        assert response.status_code == 401

    response = client.post(
        "/login",
        data={"username": "rate-limit-test", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 429
