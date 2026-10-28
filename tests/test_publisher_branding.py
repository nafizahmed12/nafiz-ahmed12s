from app import app


def test_about_page_uses_global_tech_publisher_branding():
    with app.test_client() as client:
        response = client.get("/about")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "NafizTech" in body
    assert "Independent technology publication" in body
    assert "phones, gadgets, AI and technology" in body.lower()
    assert "Nafiz Ecommerce" not in body
    assert "online shopping" not in body.lower()


def test_about_page_canonical_ignores_tracking_query_parameters():
    with app.test_client() as client:
        response = client.get("/about?utm_source=newsletter&ref=campaign")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<link rel="canonical" href="http://localhost/about">' in body
    assert "utm_source" not in body
    assert "ref=campaign" not in body
