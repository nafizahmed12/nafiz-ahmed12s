import xml.etree.ElementTree as ET


def test_sitemap_contains_only_public_canonical_urls(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://nafiz-ahmed12s.onrender.com")
    from wsgi import app

    client = app.test_client()
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    root = ET.fromstring(response.data)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locations = [node.text for node in root.findall(f"{namespace}url/{namespace}loc")]

    assert "https://nafiz-ahmed12s.onrender.com/" in locations
    assert "https://nafiz-ahmed12s.onrender.com/shop" in locations
    assert "https://nafiz-ahmed12s.onrender.com/privacy-policy" in locations
    assert "https://nafiz-ahmed12s.onrender.com/iphone-18" in locations
    assert "https://nafiz-ahmed12s.onrender.com/phone-detail/iphone-18-pro-max" in locations

    forbidden = ("/admin", "/dashboard", "/account", "/cart", "/checkout", "/user-login", "/register")
    assert not any(any(path in loc for path in forbidden) for loc in locations)
    assert all("?" not in loc for loc in locations)
