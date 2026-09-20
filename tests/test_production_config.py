import os

import pytest

from app import app


PRODUCTION_REQUIRED = (
    "SECRET_KEY",
    "DATABASE_URL",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "APP_BASE_URL",
)
PAYMENT_REQUIRED = (
    "SSLCOMMERZ_STORE_ID",
    "SSLCOMMERZ_STORE_PASSWORD",
    "PAYMENT_WEBHOOK_SECRET",
)
BKASH_REQUIRED = (
    "BKASH_USERNAME",
    "BKASH_PASSWORD",
    "BKASH_APP_KEY",
    "BKASH_APP_SECRET",
)


def _set_production_env(monkeypatch):
    values = {
        "SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql://user:password@localhost:5432/nafiz",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "strong-admin-password",
        "APP_BASE_URL": "https://example.com",
        "SESSION_COOKIE_SECURE": "1",
        "USE_SQLITE": "0",
        "SSLCOMMERZ_SANDBOX": "0",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_production_requires_core_environment_variables(monkeypatch):
    _set_production_env(monkeypatch)
    for key in PRODUCTION_REQUIRED:
        monkeypatch.delenv(key, raising=False)
        assert not os.getenv(key), f"{key} must be supplied in production"
        monkeypatch.setenv(key, "configured")


def test_production_uses_postgresql_and_secure_sessions(monkeypatch):
    _set_production_env(monkeypatch)

    assert os.getenv("USE_SQLITE") != "1"
    assert os.getenv("DATABASE_URL", "").startswith(("postgresql://", "postgresql+psycopg2://"))
    assert os.getenv("SESSION_COOKIE_SECURE") == "1"


def test_production_uses_https_base_url(monkeypatch):
    _set_production_env(monkeypatch)

    base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
    assert base_url.startswith("https://")
    assert base_url != "https://nafiz-ahmed12s.onrender.com"


def test_production_payment_credentials_are_configured(monkeypatch):
    _set_production_env(monkeypatch)
    for key in PAYMENT_REQUIRED:
        monkeypatch.setenv(key, "configured-secret")
    assert all(os.getenv(key) for key in PAYMENT_REQUIRED)
    assert os.getenv("SSLCOMMERZ_SANDBOX") == "0"


def test_production_bkash_credentials_are_configured(monkeypatch):
    _set_production_env(monkeypatch)
    for key in BKASH_REQUIRED:
        monkeypatch.setenv(key, "configured-secret")
    assert all(os.getenv(key) for key in BKASH_REQUIRED)


def test_production_session_cookie_is_secure(monkeypatch):
    _set_production_env(monkeypatch)
    with app.test_request_context("/"):
        assert app.config["SESSION_COOKIE_SECURE"] is True


def test_production_configuration_rejects_sqlite(monkeypatch):
    _set_production_env(monkeypatch)
    monkeypatch.setenv("USE_SQLITE", "1")
    assert os.getenv("USE_SQLITE") == "1"
    pytest.fail("Production must not enable USE_SQLITE=1")


def test_production_configuration_rejects_http_base_url(monkeypatch):
    _set_production_env(monkeypatch)
    monkeypatch.setenv("APP_BASE_URL", "http://example.com")
    assert not os.getenv("APP_BASE_URL", "").startswith("https://")
    pytest.fail("Production APP_BASE_URL must use HTTPS")
