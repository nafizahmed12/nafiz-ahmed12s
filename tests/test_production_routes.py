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
