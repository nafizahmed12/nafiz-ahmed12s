import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("RENDER", "0")


def test_operations_route_is_registered_and_owner_only():
    import wsgi

    routes = {rule.rule for rule in wsgi.app.url_map.iter_rules()}
    assert "/admin/operations" in routes
    response = wsgi.app.test_client().get("/admin/operations")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_integration_status_never_exposes_secret_values(monkeypatch):
    from admin_operations_routes import integration_status

    monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "pub-1234567890123456")
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", '{"private_key":"do-not-display"}')

    result = integration_status()
    assert result["adsense"]["configured"] is True
    assert result["google_analytics"]["configured"] is True
    assert "do-not-display" not in repr(result)
    assert "private_key" not in repr(result)


def test_integration_status_marks_missing_credentials_as_not_configured(monkeypatch):
    from admin_operations_routes import integration_status

    for key in ("ADSENSE_PUBLISHER_ID", "GA4_PROPERTY_ID", "GA4_SERVICE_ACCOUNT_JSON"):
        monkeypatch.delenv(key, raising=False)

    result = integration_status()
    assert result["adsense"]["configured"] is False
    assert result["google_analytics"]["configured"] is False


def test_operations_page_template_has_health_and_setup_sections():
    from pathlib import Path

    template = Path("templates/admin_operations.html").read_text(encoding="utf-8")
    assert "Database connectivity" in template
    assert "Integration readiness" in template
    assert "SEO endpoints" in template
    assert "{% include 'admin_unified_nav.html' %}" in template
