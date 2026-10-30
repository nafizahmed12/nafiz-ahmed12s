import article_publish_api
from flask import Flask


class FakeResult:
    def scalar_one(self):
        return 42


class FakeDB:
    def __init__(self):
        self.committed = False
        self.params = None

    def execute(self, statement, params):
        self.params = params
        return FakeResult()

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def make_client(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    article_publish_api.register_article_publish_api(app)
    monkeypatch.setenv("ARTICLE_PUBLISH_API_TOKEN", "test-secret-token")
    return app.test_client()


def test_publish_api_rejects_missing_or_invalid_bearer_token(monkeypatch):
    client = make_client(monkeypatch)
    response = client.post("/api/articles", json={"title": "Test"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_publish_api_requires_configured_token(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.delenv("ARTICLE_PUBLISH_API_TOKEN")
    response = client.post(
        "/api/articles",
        headers={"Authorization": "Bearer test-secret-token"},
        json={"title": "Test"},
    )
    assert response.status_code == 503


def test_publish_api_validates_article_before_database_write(monkeypatch):
    client = make_client(monkeypatch)
    db = FakeDB()
    monkeypatch.setattr(article_publish_api, "SessionLocal", lambda: db)
    response = client.post(
        "/api/articles",
        headers={"Authorization": "Bearer test-secret-token"},
        json={"title": "Test", "content": "too short"},
    )
    assert response.status_code == 400
    assert db.committed is False


def test_publish_api_creates_valid_article_and_returns_id(monkeypatch):
    client = make_client(monkeypatch)
    db = FakeDB()
    monkeypatch.setattr(article_publish_api, "SessionLocal", lambda: db)
    response = client.post(
        "/api/articles",
        headers={"Authorization": "Bearer test-secret-token"},
        json={
            "title": "A Smartphone Guide",
            "slug": "a-smartphone-guide",
            "excerpt": "A useful guide.",
            "content": "This is a sufficiently long article body for the publishing API test.",
            "category": "Smartphones",
            "featured_image_url": "",
            "seo_description": "A useful smartphone guide.",
            "status": "draft",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["id"] == 42
    assert response.get_json()["status"] == "draft"
    assert db.committed is True
    assert db.params["slug"] == "a-smartphone-guide"
