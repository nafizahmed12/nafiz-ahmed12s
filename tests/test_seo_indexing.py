from urllib.parse import urlparse

from app import app


def test_sitemap_is_absolute_canonical_public_urls():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        body = response.get_data(as_text=True)

    assert "<urlset" in body
    assert "?" not in body
    assert "/static/" not in body

    urls = [
        line.split("<loc>", 1)[1].split("</loc>", 1)[0]
        for line in body.splitlines()
        if "<loc>" in line
    ]
    assert urls
    assert all(urlparse(url).scheme == "https" for url in urls)
    assert all(urlparse(url).netloc for url in urls)


def test_sitemap_contains_primary_seo_landing_pages():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        body = client.get("/sitemap.xml").get_data(as_text=True)

    for path in (
        "/iphone-18-series",
        "/iphone-18",
        "/iphone-18-pro",
        "/iphone-18-pro-max",
        "/iphone-18-comparison",
    ):
        assert path in body


def test_robots_disallows_private_and_transactional_paths():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/robots.txt")
        assert response.status_code == 200
        body = response.get_data(as_text=True)

    for path in (
        "/admin",
        "/login",
        "/dashboard",
        "/account",
        "/register",
        "/user-login",
        "/forgot-password",
        "/reset-password",
    ):
        assert f"Disallow: {path}" in body

    assert "Sitemap: " in body
    assert "/sitemap.xml" in body
