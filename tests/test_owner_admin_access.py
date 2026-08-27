import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def test_authenticated_user_cannot_access_admin_dashboard():
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 999999
        session["username"] = "regular-user"
        session["user_session_created_at"] = 1

    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_cannot_access_admin_product_api():
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 999999
        session["username"] = "regular-user"
        session["user_session_created_at"] = 1

    response = client.get("/api/admin/products")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_authenticated_user_cannot_archive_admin_product():
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 999999
        session["username"] = "regular-user"
        session["user_session_created_at"] = 1

    response = client.post("/api/admin/products/1/archive")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin authentication required."}


def test_forged_admin_session_with_wrong_owner_username_is_rejected():
    with client.session_transaction() as session:
        session.clear()
        session["admin_logged_in"] = True
        session["admin_role"] = "admin"
        session["admin_username"] = "not-the-owner"
        session["admin_authenticated_at"] = 9999999999
        session["admin_last_activity"] = 9999999999

    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
