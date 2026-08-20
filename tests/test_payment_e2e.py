import hashlib
import hmac
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import text

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "ci-payment-secret")

import app
from database import SessionLocal, engine
import payment_routes


pytestmark = pytest.mark.integration


@pytest.fixture
def payment_fixture():
    if engine.dialect.name != "postgresql":
        pytest.skip("Payment E2E tests require PostgreSQL")

    token = uuid4().hex[:12]
    username = f"pay_{token}"
    email = f"pay_{token}@example.test"
    slug = f"pay-product-{token}"

    with SessionLocal() as db:
        user_id = db.execute(
            text("""INSERT INTO users (username,email,password_hash,created_at)
                     VALUES (:username,:email,:password_hash,NOW()) RETURNING id"""),
            {"username": username, "email": email, "password_hash": "payment-e2e-hash"},
        ).scalar_one()
        product_id = db.execute(
            text("""INSERT INTO products
                     (category_id,owner_id,name,slug,description,product_type,status,
                      price,currency,sku,stock_quantity,created_at,updated_at)
                     VALUES (NULL,NULL,'Payment E2E Product',:slug,'','physical','published',
                             125.00,'BDT',:sku,5,NOW(),NOW()) RETURNING id"""),
            {"slug": slug, "sku": f"PAY-{token}"},
        ).scalar_one()
        db.commit()

    try:
        client = app.app.test_client()
        with client.session_transaction() as session:
            session.clear()
            session.permanent = True
            session["user_id"] = user_id
            session["username"] = username
        yield client, user_id, product_id
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM commerce_orders WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM checkouts WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id=:user_id)"), {"user_id": user_id})
            db.execute(text("DELETE FROM carts WHERE user_id=:user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM products WHERE id=:product_id"), {"product_id": product_id})
            db.execute(text("DELETE FROM users WHERE id=:user_id"), {"user_id": user_id})
            db.commit()


def make_order(client, product_id):
    response = client.post("/api/cart/items", json={"product_id": product_id, "quantity": 1})
    assert response.status_code == 201
    response = client.post("/api/checkout")
    assert response.status_code == 201
    checkout_id = response.get_json()["checkout_id"]
    response = client.post(f"/api/checkout/{checkout_id}/place-order")
    assert response.status_code == 201
    return response.get_json()


def sign_payload(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"ci-payment-secret", raw, hashlib.sha256).hexdigest()
    return raw, signature


def test_payment_create_and_signed_webhook_marks_order_paid(payment_fixture):
    client, user_id, product_id = payment_fixture
    order = make_order(client, product_id)

    response = client.post(
        f"/api/orders/{order['order_id']}/payments",
        json={"provider": "manual", "transaction_id": "MANUAL-E2E-001"},
    )
    assert response.status_code == 201
    payment = response.get_json()["payment"]
    assert payment["status"] == "pending"

    payload = {
        "payment_id": payment["id"],
        "status": "paid",
        "transaction_id": "MANUAL-E2E-001",
        "provider_reference": "REF-E2E-001",
    }
    raw, signature = sign_payload(payload)
    response = client.post(
        "/api/payments/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Payment-Signature": signature},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "paid"

    response = client.get(f"/api/orders/{order['order_id']}")
    assert response.status_code == 200
    assert response.get_json()["payment_status"] == "paid"
    assert response.get_json()["status"] == "confirmed"


def test_signed_webhook_is_idempotent(payment_fixture):
    client, user_id, product_id = payment_fixture
    order = make_order(client, product_id)
    response = client.post(
        f"/api/orders/{order['order_id']}/payments",
        json={"provider": "manual", "transaction_id": "MANUAL-IDEMP-001"},
    )
    assert response.status_code == 201
    payment_id = response.get_json()["payment"]["id"]

    payload = {"payment_id": payment_id, "status": "paid", "transaction_id": "MANUAL-IDEMP-001"}
    raw, signature = sign_payload(payload)
    headers = {"X-Payment-Signature": signature}
    first = client.post("/api/payments/webhook", data=raw, content_type="application/json", headers=headers)
    second = client.post("/api/payments/webhook", data=raw, content_type="application/json", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["idempotent"] is True


def test_sslcommerz_success_callback_requires_server_validation(payment_fixture, monkeypatch):
    client, user_id, product_id = payment_fixture
    order = make_order(client, product_id)
    response = client.post(
        f"/api/orders/{order['order_id']}/payments",
        json={"provider": "sslcommerz", "transaction_id": "SSL-E2E-001"},
    )
    assert response.status_code == 201
    payment_id = response.get_json()["payment"]["id"]

    monkeypatch.setattr(
        payment_routes,
        "_ssl_validate",
        lambda val_id=None, tran_id=None: {
            "status": "VALID",
            "tran_id": "SSL-E2E-001",
            "val_id": "VAL-E2E-001",
            "amount": "125.00",
            "currency": "BDT",
        },
    )

    response = client.post(
        "/api/payments/sslcommerz/success",
        data={"tran_id": "SSL-E2E-001", "val_id": "VAL-E2E-001"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/payment/success?order_id=" in response.headers["Location"]

    with SessionLocal() as db:
        row = db.execute(
            text("SELECT status FROM payments WHERE id=:payment_id"),
            {"payment_id": payment_id},
        ).scalar_one()
        assert row == "paid"


def test_webhook_rejects_invalid_signature(payment_fixture):
    client, user_id, product_id = payment_fixture
    payload = {"payment_id": 1, "status": "paid", "transaction_id": "INVALID"}
    raw = json.dumps(payload).encode()
    response = client.post(
        "/api/payments/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Payment-Signature": "not-valid"},
    )
    assert response.status_code == 401
