import os

from app import app


def test_wsgi_import_does_not_register_a_duplicate_ads_txt_endpoint():
    import wsgi

    rules = [rule for rule in wsgi.app.url_map.iter_rules() if rule.rule == "/ads.txt"]
    assert len(rules) == 1


def test_adsense_setup_is_disabled_without_publisher_id(monkeypatch):
    monkeypatch.delenv("ADSENSE_PUBLISHER_ID", raising=False)
    with app.test_client() as client:
        response = client.get("/ads.txt")
        assert response.status_code == 404


def test_adsense_ads_txt_and_head_are_enabled_with_publisher_id(monkeypatch):
    monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "pub-1234567890123456")
    with app.test_client() as client:
        ads_txt = client.get("/ads.txt")
        assert ads_txt.status_code == 200
        assert ads_txt.get_data(as_text=True).strip() == (
            "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"
        )

        home = client.get("/")
        assert home.status_code == 200
        body = home.get_data(as_text=True)
        assert "ca-pub-1234567890123456" in body
        assert "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" in body


def test_adsense_head_is_not_injected_into_private_pages(monkeypatch):
    monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "pub-1234567890123456")
    with app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "ca-pub-1234567890123456" not in body
