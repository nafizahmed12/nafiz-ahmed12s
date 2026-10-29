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
