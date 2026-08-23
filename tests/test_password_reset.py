import os
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app
from schema import create_password_reset_token, create_user, reset_password_with_token
from database import SessionLocal
from models import User

client = app.app.test_client()


def test_init_db_creates_password_reset_tokens_table():
    """A fresh environment that bootstraps via init_db() (not `alembic upgrade
    head`) must still get a working password-reset flow. This reproduces a
    real fresh-clone/fresh-deploy scenario: brand-new SQLite file, only
    init_db() run, no migrations. password_reset_tokens must exist afterward,
    or create_password_reset_token()/reset_password_with_token() will raise
    OperationalError the first time anyone requests a reset.

    init_db() reads the module-level `database.engine` global (frozen at
    import time from whatever DATABASE_URL was set then) rather than
    re-reading DATABASE_URL on each call, so this test swaps that engine
    directly for a fresh, isolated SQLite file and restores the original
    engine afterward -- exercising the real init_db() body with no
    reimplementation, and without disturbing the shared engine every other
    test in this suite depends on."""
    import tempfile

    from sqlalchemy import create_engine, inspect

    import database
    from database import init_db

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)  # init_db() must create the file itself

    fresh_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    original_engine = database.engine
    try:
        database.engine = fresh_engine
        init_db()

        tables = set(inspect(fresh_engine).get_table_names())
        assert "password_reset_tokens" in tables, (
            "init_db() did not create password_reset_tokens. A fresh deploy "
            "that bootstraps via init_db() instead of `alembic upgrade head` "
            "will 500 on the first password-reset request."
        )
    finally:
        database.engine = original_engine
        fresh_engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


def _post_with_csrf(path, data):
    token = "ci-reset-csrf"
    with client.session_transaction() as session:
        session["_csrf_secret"] = token
    payload = dict(data)
    payload["csrf_token"] = token
    return client.post(path, data=payload, follow_redirects=False)


def test_forgot_password_page_is_public():
    response = client.get("/forgot-password")
    assert response.status_code == 200
    assert b"Forgot your password?" in response.data


def test_forgot_password_does_not_enumerate_accounts(monkeypatch):
    monkeypatch.setattr(app, "create_password_reset_token", lambda identifier: (None, None))
    response = _post_with_csrf("/forgot-password", {"identifier": "unknown@example.com"})
    assert response.status_code == 200
    assert b"If an account matches" in response.data


def test_forgot_password_sends_reset_email(monkeypatch):
    sent = {}
    monkeypatch.setattr(app, "create_password_reset_token", lambda identifier: ("test-token", "user@example.com"))
    monkeypatch.setattr(app, "send_password_reset_email", lambda email, token: sent.update(email=email, token=token))
    response = _post_with_csrf("/forgot-password", {"identifier": "user@example.com"})
    assert response.status_code == 200
    assert sent == {"email": "user@example.com", "token": "test-token"}


def test_reset_password_requires_valid_token(monkeypatch):
    calls = {}
    monkeypatch.setattr(app, "reset_password_with_token", lambda token, password: calls.update(token=token, password=password) or True)
    response = _post_with_csrf(
        "/reset-password",
        {"token": "test-token", "password": "new-password-123", "confirm_password": "new-password-123"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user-login")
    assert calls == {"token": "test-token", "password": "new-password-123"}


def test_reset_token_can_only_be_used_once():
    suffix = uuid.uuid4().hex
    username = f"reset-test-{suffix}"
    email = f"reset-test-{suffix}@example.com"
    user = create_user(username, email, "old-password-123")
    assert user is not None

    try:
        token, token_email = create_password_reset_token(email)
        assert token is not None
        assert token_email == email

        assert reset_password_with_token(token, "new-password-123") is True
        assert reset_password_with_token(token, "another-password-123") is False
    finally:
        with SessionLocal() as db:
            db.query(User).filter(User.id == user.id).delete()
            db.commit()
