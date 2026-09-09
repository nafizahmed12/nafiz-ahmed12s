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
