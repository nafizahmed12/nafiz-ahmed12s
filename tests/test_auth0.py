import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app


client = app.app.test_client()


def test_auth0_login_route_requires_configuration():
    response = client.get("/auth0/login", follow_redirects=False)
    assert response.status_code == 503
    assert b"Auth0 is not configured" in response.data


def test_user_login_page_offers_auth0_login():
    response = client.get("/user-login")
    assert response.status_code == 200
    assert b"/auth0/login" in response.data
    assert b"Continue with Auth0" in response.data


def test_auth0_callback_requires_a_valid_authenticated_profile(monkeypatch):
    class FakeAuth0:
        async def complete_interactive_login(self, callback_url, store_options):
            return {}

        async def get_user(self, store_options):
            return None

    monkeypatch.setattr(app, "auth0_client", FakeAuth0())
    response = client.get("/auth0/callback?code=fake&state=fake", follow_redirects=False)
    assert response.status_code == 400
    assert b"Authentication did not return a user profile" in response.data
