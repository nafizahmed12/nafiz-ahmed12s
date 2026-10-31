def test_phone_catalog_routes_are_registered_by_wsgi():
    import wsgi

    routes = {rule.rule for rule in wsgi.app.url_map.iter_rules()}
    assert "/phones" in routes
    assert "/phones/<brand>" in routes
    assert "/phones/<brand>/<slug>" in routes
    assert "/compare/<left>-vs-<right>" in routes
    assert "/admin/phones" in routes


def test_phone_catalog_sitemap_contains_catalog_index():
    import wsgi

    client = wsgi.app.test_client()
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "https://nafiz-ahmed12s.onrender.com/phones" in response.get_data(as_text=True)


def test_phone_catalog_detail_has_product_and_breadcrumb_schema():
    import json
    import re

    import wsgi
    from database import SessionLocal
    from sqlalchemy import text

    with SessionLocal() as db:
        row = db.execute(text("SELECT brand, slug, specs_json FROM phone_catalog WHERE status='published' ORDER BY id LIMIT 1")).mappings().first()
    if row is None:
        return

    client = wsgi.app.test_client()
    response = client.get(f"/phones/{row['brand'].lower().replace(' ', '-')}/{row['slug']}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    schemas = [
        json.loads(payload)
        for payload in re.findall(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            flags=re.DOTALL,
        )
    ]
    product = next(schema for schema in schemas if schema.get("@type") == "Product")
    breadcrumb = next(schema for schema in schemas if schema.get("@type") == "BreadcrumbList")

    assert product["sku"] == row["slug"]
    assert breadcrumb["itemListElement"][0]["name"] == "Home"

    specs = json.loads(row["specs_json"] or "{}")
    if specs:
        assert 'id="specifications"' in html
        assert "Full Specifications" in html
        assert 'class="spec-groups"' in html
        for key in specs:
            assert key.replace("_", " ").title() in html


def test_roundups_page_renders_navigation_and_phone_hubs():
    import wsgi

    client = wsgi.app.test_client()
    response = client.get("/roundups")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Technology Roundups" in html or "Roundups" in html
    assert "Smartphone brand hubs" in html
    assert 'href="/phones?brand=Apple"' in html
    assert 'href="/phones?brand=Samsung"' in html
    assert 'href="/compare"' in html
    assert 'rel="canonical"' in html


def test_homepage_links_to_roundups_and_phone_hubs():
    import wsgi

    client = wsgi.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/roundups"' in html
    assert 'href="/phones?brand=Apple"' in html
    assert 'href="/phones?brand=Samsung"' in html

def test_phone_image_upload_accepts_supported_image_and_returns_data_url():
    from io import BytesIO
    from flask import Flask
    from werkzeug.datastructures import FileStorage
    from phone_catalog_routes import _uploaded_phone_image_data_url

    app = Flask(__name__)
    with app.test_request_context():
        from flask import request
        request.files = {"image": FileStorage(
            stream=BytesIO(b"fake-png-bytes"),
            filename="phone.png",
            content_type="image/png",
        )}
        result = _uploaded_phone_image_data_url()
    assert result.startswith("data:image/png;base64,")
    assert "fake-png-bytes" not in result


def test_phone_image_upload_rejects_non_image_files():
    import pytest
    from io import BytesIO
    from flask import Flask, request
    from werkzeug.datastructures import FileStorage
    from phone_catalog_routes import _uploaded_phone_image_data_url

    app = Flask(__name__)
    with app.test_request_context():
        request.files = {"image": FileStorage(
            stream=BytesIO(b"not-an-image"),
            filename="phone.txt",
            content_type="text/plain",
        )}
        with pytest.raises(ValueError, match="JPG, PNG, WEBP or GIF"):
            _uploaded_phone_image_data_url()


def test_phone_image_upload_rejects_files_over_one_megabyte():
    import pytest
    from io import BytesIO
    from flask import Flask, request
    from werkzeug.datastructures import FileStorage
    from phone_catalog_routes import _uploaded_phone_image_data_url

    app = Flask(__name__)
    with app.test_request_context():
        request.files = {"image": FileStorage(
            stream=BytesIO(b"x" * (1024 * 1024 + 1)),
            filename="phone.jpg",
            content_type="image/jpeg",
        )}
        with pytest.raises(ValueError, match="1 MB or smaller"):
            _uploaded_phone_image_data_url()


def test_phone_admin_post_forms_include_csrf_tokens():
    from pathlib import Path
    import re

    template = Path("templates/admin_phones.html").read_text(encoding="utf-8")
    post_forms = re.findall(r'<form\b(?=[^>]*method="post")[^>]*>(.*?)</form>', template, re.DOTALL)
    assert len(post_forms) == 3
    assert all('name="csrf_token"' in form for form in post_forms)


def test_publisher_dashboard_route_is_registered_and_requires_admin():
    import wsgi

    rules = {rule.rule for rule in wsgi.app.url_map.iter_rules()}
    assert "/admin/publisher" in rules

    response = wsgi.app.test_client().get("/admin/publisher")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_publisher_dashboard_template_exposes_editorial_tools():
    from pathlib import Path

    template = Path("templates/admin_publisher_dashboard.html").read_text(encoding="utf-8")
    assert "Publisher Dashboard" in template
    assert 'href="/admin/articles"' in template
    assert 'href="/admin/phones"' in template
    assert 'href="/sitemap.xml"' in template
    assert "SEO" in template
