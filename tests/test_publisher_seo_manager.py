from publisher_admin_routes import audit_article_seo


def test_seo_audit_flags_missing_metadata():
    result = audit_article_seo({
        "seo_description": "",
        "excerpt": "",
        "featured_image_url": "",
    })
    assert result == ["Missing SEO description", "Missing excerpt", "Missing featured image"]


def test_seo_audit_flags_description_outside_recommended_length():
    result = audit_article_seo({
        "seo_description": "Short description",
        "excerpt": "A useful summary",
        "featured_image_url": "https://example.com/image.jpg",
    })
    assert result == ["SEO description too short"]


def test_seo_audit_accepts_complete_metadata():
    result = audit_article_seo({
        "seo_description": "A practical guide to choosing a smartphone with strong battery life, a clear display, reliable performance and useful camera features.",
        "excerpt": "A practical smartphone buying guide.",
        "featured_image_url": "https://example.com/image.jpg",
    })
    assert result == []


def test_seo_manager_route_is_registered_and_admin_only():
    import wsgi

    routes = {rule.rule for rule in wsgi.app.url_map.iter_rules()}
    assert "/admin/seo" in routes
    response = wsgi.app.test_client().get("/admin/seo")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_seo_manager_template_explains_read_only_audit():
    from pathlib import Path

    template = Path("templates/admin_publisher_seo.html").read_text(encoding="utf-8")
    assert "Read-only article metadata audit" in template
    assert "120–160 characters" in template
    assert 'href="/admin/seo"' in Path("templates/admin_publisher_dashboard.html").read_text(encoding="utf-8")
