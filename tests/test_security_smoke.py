import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")
os.environ.setdefault("RENDER", "0")

import app
from database import SessionLocal
from payment_routes import _money
from sqlalchemy import text


client = app.app.test_client()


def test_money_normalizes_decimal_amounts():
    assert _money("100") == "100.00"
    assert _money("100.5") == "100.50"
    assert _money("0") == "0.00"


def test_money_rejects_invalid_amounts_safely():
    assert _money("not-a-number") == "0.00"
    assert _money(None) == "0.00"


# --- Form CSRF (csrf.py's _valid_csrf_token, enforced via _check_csrf) ---
#
# /login is handled by admin_security.py's handle_admin_login_from_db, a
# before_request hook registered ahead of csrf.py's _check_csrf, so it is
# the route where a CSRF gap would be easiest to introduce silently: a
# short-circuiting hook that runs earlier never reaches csrf.py's check at
# all. These tests exercise that real path end-to-end rather than csrf.py's
# helpers in isolation, since an isolated unit test would not have caught
# the hook-ordering bug this file was written to cover.


def _reset_login_rate_limit(username):
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM login_rate_limits WHERE rate_key LIKE :key"),
            {"key": f"%:{username}"},
        )
        db.commit()


def test_login_rejects_missing_csrf_token():
    _reset_login_rate_limit("ci-admin")
    response = client.post(
        "/login", data={"username": "ci-admin", "password": "ci-password"}
    )
    assert response.status_code == 400
    with client.session_transaction() as session:
        assert not session.get("admin_logged_in")


def test_login_rejects_wrong_csrf_token():
    _reset_login_rate_limit("ci-admin")
    with client.session_transaction() as session:
        session["_csrf_secret"] = "real-session-secret"
    response = client.post(
        "/login",
        data={
            "username": "ci-admin",
            "password": "ci-password",
            "csrf_token": "attacker-guessed-token",
        },
    )
    assert response.status_code == 400
    with client.session_transaction() as session:
        assert not session.get("admin_logged_in")


def test_login_accepts_correct_session_bound_csrf_token():
    _reset_login_rate_limit("ci-admin")
    with client.session_transaction() as session:
        session["_csrf_secret"] = "real-session-secret"
    response = client.post(
        "/login",
        data={
            "username": "ci-admin",
            "password": "ci-password",
            "csrf_token": "real-session-secret",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")
    client.get("/logout", follow_redirects=False)


# --- Origin validation for /api/ routes (csrf.py's _valid_same_origin_request) ---
#
# /api/cart/items is used as a stand-in for the whole /api/ prefix: it is a
# real POST route behind commerce_routes.py's own auth check, and Flask
# always runs before_request hooks ahead of the view body, so an
# origin-check failure here returns 400 before the route's 401
# (authentication required) is ever reached. That ordering is what lets a
# single unauthenticated request isolate the origin check from the route's
# own logic.


def test_api_post_blocks_cross_origin_request():
    response = client.post(
        "/api/cart/items",
        json={"product_id": 1, "quantity": 1},
        headers={"Origin": "https://evil.example.com"},
    )
    assert response.status_code == 400


def test_api_post_blocks_null_origin():
    # Sandboxed iframes and some redirect chains send a literal "null"
    # Origin header, which must not be treated as same-origin.
    response = client.post(
        "/api/cart/items",
        json={"product_id": 1, "quantity": 1},
        headers={"Origin": "null"},
    )
    assert response.status_code == 400


def test_api_post_blocks_cross_origin_referer_when_origin_absent():
    response = client.post(
        "/api/cart/items",
        json={"product_id": 1, "quantity": 1},
        headers={"Referer": "https://evil.example.com/some-page"},
    )
    assert response.status_code == 400


def test_api_post_allows_same_origin_request():
    response = client.post(
        "/api/cart/items",
        json={"product_id": 1, "quantity": 1},
        headers={"Origin": "http://localhost"},
    )
    # Origin check passes and the request reaches the route's own auth
    # check; 400 (blocked by CSRF) would indicate a same-origin regression.
    assert response.status_code == 401


def test_api_post_allows_request_with_no_origin_or_referer():
    # Non-browser clients (server-to-server calls, curl, mobile apps) send
    # neither header. _valid_same_origin_request treats this as a case it
    # cannot evaluate and lets it through to the route's own auth check.
    response = client.post("/api/cart/items", json={"product_id": 1, "quantity": 1})
    assert response.status_code == 401


def test_sslcommerz_webhook_path_is_exempt_from_origin_check():
    # Payment provider callbacks are server-to-server and never carry a
    # same-origin Origin/Referer; this path's trust boundary is signature
    # validation, not browser-origin metadata. A forged cross-origin Origin
    # header must not be blocked by the origin check specifically -- proven
    # by checking the exact error body: an empty tran_id fails the route's
    # own validation with "tran_id is required" before any database query
    # runs, which is a different, unambiguous 400 from the origin check's
    # "Cross-origin API request blocked."
    response = client.post(
        "/api/payments/sslcommerz/success",
        data={"tran_id": ""},
        headers={"Origin": "https://evil.example.com"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "tran_id is required."
