from app import app


def test_public_trust_pages_are_available():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        for path in ("/about", "/contact", "/privacy-policy", "/terms", "/refund-policy"):
            response = client.get(path)
            assert response.status_code == 200, path


def test_sitemap_contains_public_trust_pages():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        for path in ("/about", "/contact", "/privacy-policy", "/terms", "/refund-policy"):
            assert path in body
