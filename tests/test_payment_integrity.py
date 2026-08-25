import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "webhook-secret")

import hashlib
import hmac
import json

import app


client = app.app.test_client()


def _signed_webhook(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"webhook-secret", raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/payments/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Payment-Signature": signature},
    )


def test_paid_payment_cannot_be_downgraded_by_later_webhook():
    """A terminal paid state must not be overwritten by a stale failure/cancel event."""
    # This regression test exercises the state-transition helper directly so it
    # does not depend on the rest of commerce order creation in the test suite.
    from database import SessionLocal
    from sqlalchemy import text
    from payment_routes import _apply_payment_status

    with SessionLocal() as db:
        user_id = db.execute(
            text("INSERT INTO users(username,email,password_hash) VALUES ('payment-test','payment-test@example.com','x') RETURNING id")
        ).scalar_one()
        order_id = db.execute(
            text("""INSERT INTO commerce_orders(user_id,order_number,status,payment_status,currency,total_amount,created_at,updated_at)
                    VALUES (:user_id,'TEST-PAY-1','confirmed','paid','BDT',100.00,NOW(),NOW()) RETURNING id"""),
            {"user_id": user_id},
        ).scalar_one()
        payment_id = db.execute(
            text("""INSERT INTO payments(order_id,provider,status,amount,currency,created_at,updated_at)
                    VALUES (:order_id,'sslcommerz','paid',100.00,'BDT',NOW(),NOW()) RETURNING id"""),
            {"order_id": order_id},
        ).scalar_one()
        db.commit()

        payment = db.execute(
            text("SELECT id FROM payments WHERE id=:payment_id FOR UPDATE"),
            {"payment_id": payment_id},
        ).mappings().one()
        _apply_payment_status(db, order_id, payment["id"], "failed")
        db.commit()

        row = db.execute(
            text("SELECT status FROM payments WHERE id=:payment_id"),
            {"payment_id": payment_id},
        ).scalar_one()
        assert row == "paid"
