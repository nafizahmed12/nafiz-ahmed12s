import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
os.environ.setdefault("ADMIN_USERNAME", "ci-admin")
os.environ.setdefault("ADMIN_PASSWORD", "ci-password")

import app  # noqa: E402  (loads app.wsgi_app = ProxyFix(..., x_for=1, ...), same as production)

client = app.app.test_client()


# digital_affiliate_routes.py's affiliate_click() hashes "the client IP" for
# affiliate_clicks.ip_hash. Every other IP-keyed spot in this codebase (the
# rate limiters in app.py/commerce_routes.py/payment_routes.py/bkash_routes.py/
# admin_security.py) reads request.remote_addr, which app.py's
# ProxyFix(x_for=1, ...) has already resolved from X-Forwarded-For, trusting
# exactly one hop and discarding anything a client prepends before it.
#
# affiliate_click() instead read the X-Forwarded-For header directly. That
# header is ordinary attacker-controlled request input, not a value ProxyFix
# has vetted -- a client can set it to any string, including extra fake
# comma-separated hops. Reading it raw meant a spoofed multi-hop header got
# hashed whole instead of the single real IP ProxyFix already resolved,
# disagreeing with what every other part of the app calls "the IP".
#
# This drives a real request through client.get() (the actual ProxyFix-
# wrapped WSGI stack) and reads request.remote_addr back out via
# error_handlers.py's own permanent "request_complete" log line -- the app's
# own already-registered instrumentation -- rather than registering a new
# after_request hook, since Flask locks hook registration once the shared
# app object (reused across every test file in this suite) has served its
# first request.


def test_proxyfix_resolves_remote_addr_to_the_trusted_hop_only(caplog):
    with caplog.at_level("INFO"):
        client.get(
            "/health",
            headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.9"},
            environ_overrides={"REMOTE_ADDR": "10.0.0.1"},
        )

    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("request_complete")]
    assert lines, "expected error_handlers.py's request_complete log line"
    remote_addr = re.search(r"remote=(\S+)", lines[-1]).group(1)

    # Correct behavior (what request.remote_addr gives, and what the fixed
    # affiliate_click() now hashes): only the trusted hop.
    assert remote_addr == "203.0.113.9"

    # The vulnerable expression this test guards against would have hashed
    # this whole spoofed string instead.
    assert remote_addr != "1.2.3.4, 203.0.113.9"


def test_affiliate_click_ip_expression_uses_remote_addr_not_raw_header():
    # affiliate_profiles/affiliate_clicks only exist via the Postgres-only
    # Alembic migration chain, not the lightweight SQLite bootstrap used
    # here, so this can't drive a full DB-backed request through
    # affiliate_click() in this environment. This pins the exact source
    # line instead, so a future edit can't silently reintroduce the raw
    # X-Forwarded-For read this fix removes.
    source_path = os.path.join(os.path.dirname(__file__), "..", "digital_affiliate_routes.py")
    source = open(source_path).read()
    assert 'ip = request.remote_addr or ""' in source
    assert 'request.headers.get("X-Forwarded-For", request.remote_addr' not in source
