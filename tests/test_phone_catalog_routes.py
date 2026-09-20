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
    import wsgi
    from database import SessionLocal
    from sqlalchemy import text

    with SessionLocal() as db:
        row = db.execute(text("SELECT brand, slug FROM phone_catalog WHERE status='published' ORDER BY id LIMIT 1")).mappings().first()
    if row is None:
        return

    client = wsgi.app.test_client()
    response = client.get(f"/phones/{row['brand'].lower().replace(' ', '-')}/{row['slug']}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '"@type":"Product"' in html
    assert '"sku":"' + row['slug'] + '"' in html
    assert '"@type":"BreadcrumbList"' in html
