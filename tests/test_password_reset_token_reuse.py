import hashlib
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import User
from schema import create_password_reset_token, reset_password_with_token
from sqlalchemy import text


def test_password_reset_token_is_single_use():
    username = "reset-reuse-test"
    email = "reset-reuse@example.com"
    with SessionLocal() as db:
        db.execute(text("DELETE FROM password_reset_tokens WHERE token_hash IS NOT NULL"))
        db.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        db.commit()

    with SessionLocal() as db:
        user = User(username=username, email=email, password_hash="placeholder")
        db.add(user)
        db.commit()

    token, returned_email = create_password_reset_token(email)
    assert token and returned_email == email
    assert reset_password_with_token(token, "first-password-123") is True
    assert reset_password_with_token(token, "second-password-123") is False


def test_expired_password_reset_token_is_rejected():
    email = "reset-expired@example.com"
    with SessionLocal() as db:
        db.execute(text("DELETE FROM password_reset_tokens WHERE token_hash IS NOT NULL"))
        db.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        user = User(username="reset-expired-test", email=email, password_hash="placeholder")
        db.add(user)
        db.commit()
        db.refresh(user)
        token = "expired-test-token"
        db.execute(
            text("""INSERT INTO password_reset_tokens
                (user_id, token_hash, expires_at, created_at)
                VALUES (:uid, :hash, :expires, :created)"""),
            {
                "uid": user.id,
                "hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "expires": datetime.now(timezone.utc) - timedelta(minutes=1),
                "created": datetime.now(timezone.utc) - timedelta(minutes=31),
            },
        )
        db.commit()

    assert reset_password_with_token(token, "expired-password-123") is False
