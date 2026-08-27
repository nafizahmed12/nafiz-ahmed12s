import os
import time

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_IDLE_TIMEOUT_SECONDS", "1800")
os.environ.setdefault("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def _regular_user_session():
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 999999
        session["username"] = "regular-user"
        session["user_session_created_at"] = time.time()


def _forged_admin_session(**overrides):
    values = {
        "admin_logged_in": True,
        "admin_role": "admin",
        "admin_username": "not-the-owner",
        "admin_authenticated_at": time.time(),
        "admin_last_activity": time.time(),
    }
    values.update(overrides)
    with client.session_transaction() as session:
        session.clear()
        session.update(values)


def test_authenticated_user_cannot_access_admin_dashboard():
    _regular_user_session()
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_cannot_access_admin_product_api():
    _regular_user_session()
    response = client.get("/api/admin/products")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_authenticated_user_cannot_archive_admin_product():
    _regular_user_session()
    response = client.post("/api/admin/products/1/archive")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_authenticated_user_cannot_create_admin_product():
    _regular_user_session()
    response = client.post("/admin/products", data={"name": "Unauthorized"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_cannot_access_admin_orders():
    _regular_user_session()
    response = client.get("/admin/orders")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_cannot_read_admin_order_api():
    _regular_user_session()
    response = client.get("/api/admin/orders")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_authenticated_user_cannot_update_admin_order():
    _regular_user_session()
    response = client.patch("/api/admin/orders/1", json={"status": "completed"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_forged_admin_session_with_wrong_owner_username_is_rejected():
    _forged_admin_session()
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_forged_admin_session_with_expired_idle_timeout_is_rejected():
    _forged_admin_session(
        admin_username="ci-admin",
        admin_authenticated_at=time.time(),
        admin_last_activity=time.time() - 3601,
    )
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_forged_admin_session_with_expired_absolute_timeout_is_rejected():
    _forged_admin_session(
        admin_username="ci-admin",
        admin_authenticated_at=time.time() - 43201,
        admin_last_activity=time.time(),
    )
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_cannot_publish_digital_product():
    _regular_user_session()
    response = client.post(
        "/api/digital-products",
        json={
            "name": "Unauthorized product",
            "slug": "unauthorized-product",
            "price": "100",
            "delivery_url": "https://example.com/file",
        },
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_forged_admin_session_cannot_publish_digital_product():
    _forged_admin_session()
    response = client.post(
        "/api/digital-products",
        json={
            "name": "Forged product",
            "slug": "forged-product",
            "price": "100",
            "delivery_url": "https://example.com/file",
        },
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}
