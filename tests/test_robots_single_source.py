from app import app


def test_robots_and_sitemap_have_single_route_source():
    robots_rules = [rule for rule in app.url_map.iter_rules() if rule.rule == "/robots.txt"]
    sitemap_rules = [rule for rule in app.url_map.iter_rules() if rule.rule == "/sitemap.xml"]

    assert len(robots_rules) == 1
    assert len(sitemap_rules) == 1


def test_robots_response_allows_public_seo_pages_and_blocks_private_paths():
    client = app.test_client()
    response = client.get("/robots.txt")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "User-agent: *" in body
    assert "Allow: /" in body
    for path in (
        "/iphone-18",
        "/iphone-18-pro",
        "/iphone-18-pro-max",
        "/iphone-18-series",
        "/iphone-18-comparison",
    ):
        assert f"Allow: {path}" in body
    for path in (
        "/admin",
        "/login",
        "/dashboard",
        "/account",
        "/checkout",
        "/orders",
        "/api/",
    ):
        assert f"Disallow: {path}" in body
    assert "Disallow: /\n" not in body
    assert "Sitemap: https://nafiz-ahmed12s.onrender.com/sitemap.xml" in body
