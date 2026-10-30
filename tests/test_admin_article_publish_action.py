import time

import blog_routes
from flask import Flask


class FakeResult:
    rowcount = 1

    def mappings(self):
        return self


class FakeDB:
    def __init__(self, existing=True):
        self.existing = existing
        self.params = None
        self.executions = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, params):
        self.params = params
        self.executions.append((str(statement), params))
        if "SELECT id FROM blog_articles" in str(statement):
            return type("Lookup", (), {
                "mappings": lambda self: self,
                "first": lambda lookup: {"id": 7} if self.existing else None,
            })()
        return FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def make_client(monkeypatch, db):
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setattr(blog_routes, "SessionLocal", lambda: db)
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(blog_routes.blog_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        now = time.time()
        session.update({
            "admin_logged_in": True,
            "admin_role": "admin",
            "admin_username": "owner",
            "admin_authenticated_at": now,
            "admin_last_activity": now,
        })
    return client


def test_publish_draft_requires_valid_admin_session(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(blog_routes, "SessionLocal", lambda: db)
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(blog_routes.blog_bp)

    @app.get("/login")
    def login():
        return "Login", 200

    response = app.test_client().post("/admin/articles/7/publish")
    assert response.status_code == 302
    assert response.location.endswith("/login")
    assert db.committed is False


def test_publish_draft_sets_status_and_published_timestamp(monkeypatch):
    db = FakeDB()
    client = make_client(monkeypatch, db)
    response = client.post("/admin/articles/7/publish")
    assert response.status_code == 302
    assert response.location.endswith("/admin/articles")
    assert db.committed is True
    update_sql, update_params = db.executions[-1]
    assert "status='published'" in update_sql
    assert "published_at=COALESCE(published_at, :now)" in update_sql
    assert update_params["id"] == 7
    assert update_params["now"] is not None


def test_publish_missing_article_returns_not_found(monkeypatch):
    db = FakeDB(existing=False)
    client = make_client(monkeypatch, db)
    response = client.post("/admin/articles/404/publish")
    assert response.status_code == 404
    assert db.committed is False
