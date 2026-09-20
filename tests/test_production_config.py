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


def require_production_audit():
    if os.getenv("RUN_PRODUCTION_CONFIG_AUDIT") != "1":
        pytest.skip("Set RUN_PRODUCTION_CONFIG_AUDIT=1 on the deployment host to run the production configuration audit")


def test_production_has_core_environment_variables():
    require_production_audit()
    missing = [key for key in PRODUCTION_REQUIRED if not os.getenv(key, "").strip()]
    assert not missing, f"Missing production environment variables: {', '.join(missing)}"


def test_production_uses_postgresql_and_secure_sessions():
    require_production_audit()
    database_url = os.getenv("DATABASE_URL", "").strip().lower()
    assert os.getenv("USE_SQLITE", "0") != "1", "USE_SQLITE=1 must not be enabled in production"
    assert database_url.startswith(("postgresql://", "postgresql+psycopg2://")), "Production DATABASE_URL must use PostgreSQL"
    assert os.getenv("SESSION_COOKIE_SECURE") == "1", "SESSION_COOKIE_SECURE=1 is required for HTTPS production"


def test_production_uses_https_base_url():
    require_production_audit()
    base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    assert base_url.startswith("https://"), "APP_BASE_URL must use HTTPS in production"


def test_production_payment_credentials_are_configured():
    if os.getenv("RUN_PAYMENT_CONFIG_AUDIT") != "1":
        pytest.skip("Set RUN_PAYMENT_CONFIG_AUDIT=1 to require live payment credentials")
    missing = [key for key in PAYMENT_REQUIRED if not os.getenv(key, "").strip()]
    assert not missing, f"Missing payment environment variables: {', '.join(missing)}"
    assert os.getenv("SSLCOMMERZ_SANDBOX") == "0", "SSLCOMMERZ_SANDBOX=0 is required for live payments"


def test_production_bkash_credentials_are_configured():
    if os.getenv("RUN_PAYMENT_CONFIG_AUDIT") != "1":
        pytest.skip("Set RUN_PAYMENT_CONFIG_AUDIT=1 to require live payment credentials")
    missing = [key for key in BKASH_REQUIRED if not os.getenv(key, "").strip()]
    assert not missing, f"Missing bKash environment variables: {', '.join(missing)}"


def test_loaded_flask_config_uses_secure_session_cookie():
    require_production_audit()
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_production_does_not_use_the_render_default_url():
    require_production_audit()
    assert os.getenv("APP_BASE_URL", "").strip().rstrip("/") != "https://nafiz-ahmed12s.onrender.com"
