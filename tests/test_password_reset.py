import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app

client = app.app.test_client()


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
