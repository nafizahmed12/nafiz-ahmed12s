import os
import time
from uuid import uuid4

import pytest
from sqlalchemy import text

# The commerce workflow relies on PostgreSQL row-locking/RETURNING semantics.
# The existing lightweight tests intentionally support SQLite, so skip this
# integration suite when the test database is not PostgreSQL.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app
from database import SessionLocal, engine


pytestmark = pytest.mark.integration


@pytest.fixture
def commerce_fixture():
    if engine.dialect.name != "postgresql":
        pytest.skip("Commerce E2E tests require PostgreSQL")

    token = uuid4().hex[:12]
    username = f"e2e_{token}"
    email = f"e2e_{token}@example.test"
    slug = f"e2e-product-{token}"

    with SessionLocal() as db:
        user_id = db.execute(
            text("""INSERT INTO users (username,email,password_hash,created_at)
                    VALUES (:username,:email,:password_hash,NOW()) RETURNING id"""),
            {"username": username, "email": email, "password_hash": "e2e-test-hash"},
        ).scalar_one()
        product_id = db.execute(
            text("""INSERT INTO products
                    (category_id,owner_id,name,slug,description,product_type,status,
                     price,currency,sku,stock_quantity,created_at,updated_at)
                    VALUES (NULL,NULL,'E2E Test Product',:slug,'','physical','published',
                            125.00,'BDT',:sku,3,NOW(),NOW()) RETURNING id"""),
            {"slug": slug, "sku": f"E2E-{token}"},
        ).scalar_one()
        db.commit()

    try:
        yield user_id, product_id
    finally:
        with SessionLocal() as db:
            # Delete the user last because carts/orders reference it.
            db.execute(text("DELETE FROM commerce_orders WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM checkouts WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id=:user_id)"), {"user_id": user_id})
            db.execute(text("DELETE FROM carts WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM products WHERE id=:product_id"), {"product_id": product_id})
            db.execute(text("DELETE FROM users WHERE id=:user_id"), {"user_id": user_id})
            db.commit()


def authenticated_client(user_id):
    client = app.app.test_client()
    with client.session_transaction() as session:
        session.clear()
        session.permanent = True
        session["user_id"] = user_id
        session["username"] = "e2e-user"
        session["user_session_created_at"] = time.time()
    return client


def test_customer_checkout_place_order_flow(commerce_fixture):
    user_id, product_id = commerce_fixture
    client = authenticated_client(user_id)

    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.get_json()["items"]
    product = next(item for item in products if item["id"] == product_id)
    assert product["price"] == "125.00"
    assert product["stock_quantity"] == 3

    response = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 201
    assert response.get_json()["item_count"] == 2
    cart_item_id = response.get_json()["items"][0]["cart_item_id"]

    response = client.post("/api/checkout")
    assert response.status_code == 201
    checkout = response.get_json()
    assert checkout["total_amount"] == "250.00"

    response = client.get(f"/api/checkout/{checkout['checkout_id']}")
    assert response.status_code == 200
    assert response.get_json()["items"][0]["quantity"] == 2

    response = client.post(f"/api/checkout/{checkout['checkout_id']}/place-order")
    assert response.status_code == 201
    order = response.get_json()
    assert order["payment_status"] == "pending"
    assert order["status"] == "pending"
    assert order["total_amount"] == "250.00"

    response = client.get(f"/api/orders/{order['order_id']}")
    assert response.status_code == 200
    order_detail = response.get_json()
    assert order_detail["order_number"] == order["order_number"]
    assert order_detail["items"][0]["quantity"] == 2

    response = client.get("/api/cart")
    assert response.status_code == 200
    assert response.get_json()["item_count"] == 0

    with SessionLocal() as db:
        stock = db.execute(
            text("SELECT stock_quantity FROM products WHERE id=:product_id"),
            {"product_id": product_id},
        ).scalar_one()
        assert stock == 1

        cart_item = db.execute(
            text("SELECT id FROM cart_items WHERE id=:cart_item_id"),
            {"cart_item_id": cart_item_id},
        ).scalar_one_or_none()
        assert cart_item is None


def test_cart_rejects_quantity_above_stock(commerce_fixture):
    user_id, product_id = commerce_fixture
    client = authenticated_client(user_id)

    response = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": 4},
    )
    assert response.status_code == 409
    assert "stock" in response.get_json()["error"].lower()


def test_checkout_rejects_when_stock_changes(commerce_fixture):
    user_id, product_id = commerce_fixture
    client = authenticated_client(user_id)

    response = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 201

    response = client.post("/api/checkout")
    assert response.status_code == 201
    checkout_id = response.get_json()["checkout_id"]

    with SessionLocal() as db:
        db.execute(
            text("UPDATE products SET stock_quantity=1 WHERE id=:product_id"),
            {"product_id": product_id},
        )
        db.commit()

    response = client.post(f"/api/checkout/{checkout_id}/place-order")
    assert response.status_code == 409
    assert "stock" in response.get_json()["error"].lower()


def test_order_detail_is_not_accessible_to_another_user(commerce_fixture):
    user_id, product_id = commerce_fixture
    owner_client = authenticated_client(user_id)

    response = owner_client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": 1},
    )
    assert response.status_code == 201

    response = owner_client.post("/api/checkout")
    assert response.status_code == 201
    checkout_id = response.get_json()["checkout_id"]

    response = owner_client.post(f"/api/checkout/{checkout_id}/place-order")
    assert response.status_code == 201
    order_id = response.get_json()["order_id"]

    token = uuid4().hex[:12]
    with SessionLocal() as db:
        other_user_id = db.execute(
            text("""INSERT INTO users (username,email,password_hash,created_at)
                    VALUES (:username,:email,:password_hash,NOW()) RETURNING id"""),
            {
                "username": f"idor_{token}",
                "email": f"idor_{token}@example.test",
                "password_hash": "idor-test-hash",
            },
        ).scalar_one()
        db.commit()

    try:
        other_client = authenticated_client(other_user_id)
        response = other_client.get(f"/api/orders/{order_id}")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Order not found."
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM carts WHERE user_id=:user_id"), {"user_id": other_user_id})
            db.execute(text("DELETE FROM users WHERE id=:user_id"), {"user_id": other_user_id})
            db.commit()
