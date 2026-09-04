from datetime import date
from urllib.parse import urlparse
from xml.etree import ElementTree

from app import app

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
PUBLIC_SEO_PATHS = (
    "/iphone-18-series",
    "/iphone-18",
    "/iphone-18-pro",
    "/iphone-18-pro-max",
    "/iphone-18-comparison",
)


def test_sitemap_is_valid_xml_with_absolute_public_urls_without_query_strings():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        body = response.get_data(as_text=True)

    root = ElementTree.fromstring(body)
    assert root.tag == f"{{{SITEMAP_NS}}}urlset"
    assert "/static/" not in body

    urls = root.findall(f"{{{SITEMAP_NS}}}url")
    assert urls
    for entry in urls:
        loc = entry.find(f"{{{SITEMAP_NS}}}loc")
        assert loc is not None
        assert loc.text == loc.text.strip()
        parsed = urlparse(loc.text)
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc
        assert parsed.query == ""


def test_sitemap_lastmod_values_are_valid_dates_when_present():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        body = client.get("/sitemap.xml").get_data(as_text=True)

    root = ElementTree.fromstring(body)
    for entry in root.findall(f"{{{SITEMAP_NS}}}url"):
        lastmod = entry.find(f"{{{SITEMAP_NS}}}lastmod")
        if lastmod is not None:
            assert lastmod.text == lastmod.text.strip()
            date.fromisoformat(lastmod.text)


def test_sitemap_contains_primary_seo_landing_pages():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        body = client.get("/sitemap.xml").get_data(as_text=True)

    for path in PUBLIC_SEO_PATHS:
        assert path in body


def test_public_seo_pages_return_indexable_html_with_self_canonicals():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        for path in PUBLIC_SEO_PATHS:
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.mimetype == "text/html", path
            body = response.get_data(as_text=True)
            assert 'name="robots" content="index,follow' in body, path
            assert '<link rel="canonical" href="https://nafiz-ahmed12s.onrender.com' in body, path
            assert 'noindex' not in body.lower(), path
            assert 'nofollow' not in body.lower(), path


def test_public_seo_pages_are_linked_from_the_cluster_hub():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        body = client.get("/iphone-18-series").get_data(as_text=True)

    for path in PUBLIC_SEO_PATHS[1:]:
        assert f'href="{path}"' in body


def test_robots_explicitly_allows_public_seo_pages():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/robots.txt")
        assert response.status_code == 200
        body = response.get_data(as_text=True)

    assert "User-agent: *" in body
    assert "Allow: /" in body
    for path in PUBLIC_SEO_PATHS:
        assert f"Allow: {path}" in body


def test_robots_disallows_private_paths_and_references_sitemap():
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
        "/checkout",
        "/orders",
        "/api/",
    ):
        assert f"Disallow: {path}" in body

    assert "Disallow: /\n" not in body
    assert "Sitemap: " in body
    assert "/sitemap.xml" in body
