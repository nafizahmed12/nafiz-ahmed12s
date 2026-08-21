import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def _csrf_token(get_path):
    """Fetch a page's CSRF token so form POSTs in these tests exercise the
    real csrf.py before_request check instead of bypassing it. Every page
    that renders a form here shares one session-bound token, so any page
    with a <form> works as the source."""
    page = client.get(get_path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
    assert match, f"No csrf_token field found on {get_path}"
    return match.group(1).decode()


def test_admin_requires_authentication():
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_admin_product_api_requires_authentication():
    response = client.get("/api/admin/products")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_admin_archive_api_requires_authentication():
    response = client.post("/api/admin/products/1/archive")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_admin_product_create_requires_authentication():
    response = client.post(
        "/admin/products",
        data={
            "csrf_token": _csrf_token("/login"),
            "name": "CI Product",
            "slug": "ci-product",
            "price": "100",
            "stock_quantity": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_supplier_register_page_is_public():
    response = client.get("/supplier/register")
    assert response.status_code == 200
    assert b"Supplier" in response.data or b"supplier" in response.data


def test_supplier_login_page_is_public():
    response = client.get("/supplier/login")
    assert response.status_code == 200
    assert b"Login" in response.data or b"login" in response.data


def test_supplier_dashboard_requires_authentication():
    response = client.get("/supplier/dashboard")
    assert response.status_code == 302
    assert "/supplier/login" in response.headers["Location"]


def test_seller_api_requires_authentication():
    for path in ("/api/seller/profile", "/api/seller/products", "/api/seller/dashboard"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required."}


def test_seller_register_requires_authentication():
    response = client.post(
        "/api/seller/register",
        json={"store_name": "CI Store", "store_slug": "ci-store"},
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_seller_product_create_requires_authentication():
    response = client.post(
        "/api/seller/products",
        json={"product_id": 1, "seller_price": "100", "seller_stock": 5},
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_seller_product_update_requires_authentication():
    response = client.patch(
        "/api/seller/products/1",
        json={"seller_stock": 10},
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_supplier_register_rejects_short_password_before_database_access():
    response = client.post(
        "/supplier/register",
        data={
            "csrf_token": _csrf_token("/supplier/register"),
            "username": "ci-supplier",
            "email": "ci-supplier@example.com",
            "password": "short",
            "company_name": "CI Supplier",
            "phone": "01700000000",
            "country": "Bangladesh",
        },
    )
    assert response.status_code == 400
    assert b"password" in response.data.lower()


def test_admin_login_rejects_invalid_credentials():
    response = client.post(
        "/login",
        data={
            "csrf_token": _csrf_token("/login"),
            "username": "wrong-admin",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data
