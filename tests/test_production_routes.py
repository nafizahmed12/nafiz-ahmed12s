import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app

client = app.app.test_client()


def _reset_admin_login_rate_limits():
    """Keep admin route tests isolated from previous runs of the SQLite test DB."""
    from database import SessionLocal
    from sqlalchemy import text

    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM login_rate_limits WHERE rate_key LIKE :prefix OR rate_key LIKE :rate_key"),
            {"prefix": "%:admin:ci-admin", "rate_key": "%:rate-limit-test"},
        )
        db.commit()


def _admin_post(path, data):
    """Submit an admin form with a session-bound CSRF token, matching production forms."""
    token = "ci-csrf-token"
    with client.session_transaction() as session:
        session["_csrf_secret"] = token
    payload = dict(data)
    payload["csrf_token"] = token
    return client.post(path, data=payload, follow_redirects=False)


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
    _reset_admin_login_rate_limits()
    response = _admin_post(
        "/login",
        {"username": "ci-admin", "password": "ci-password"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")

    with client.session_transaction() as session:
        assert session.get("admin_logged_in") is True
        assert session.get("admin_authenticated_at") is not None
        assert session.get("admin_last_activity") is not None

    client.get("/logout", follow_redirects=False)


def test_admin_login_rejects_invalid_credentials():
    _reset_admin_login_rate_limits()
    response = _admin_post(
        "/login",
        {"username": "ci-admin", "password": "wrong-password"},
    )
    assert response.status_code == 401

    with client.session_transaction() as session:
        assert not session.get("admin_logged_in")


def test_admin_logout_clears_privileged_session():
    _reset_admin_login_rate_limits()
    response = _admin_post(
        "/login",
        {"username": "ci-admin", "password": "ci-password"},
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
    _reset_admin_login_rate_limits()
    for _ in range(5):
        response = _admin_post(
            "/login",
            {"username": "rate-limit-test", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = _admin_post(
        "/login",
        {"username": "rate-limit-test", "password": "wrong-password"},
    )
    assert response.status_code == 429
