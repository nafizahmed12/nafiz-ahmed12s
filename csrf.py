import hmac
import secrets

from flask import abort, request, session


def _get_or_create_csrf_secret():
    """Per-session random value the token is bound to (separate from app.secret_key
    so a leaked token can't be replayed against a different session)."""
    value = session.get("_csrf_secret")
    if not value:
        value = secrets.token_hex(32)
        session["_csrf_secret"] = value
    return value


def generate_csrf_token():
    return _get_or_create_csrf_secret()


def _valid_csrf_token(submitted):
    if not submitted:
        return False
    expected = session.get("_csrf_secret")
    if not expected:
        return False
    return hmac.compare_digest(str(submitted), str(expected))


# Endpoints intentionally excluded from the form-CSRF check:
#  - Everything under /api/ (commerce, payment, seller, SSLCommerz
#    success/fail/cancel/ipn, digital-products, etc.) is a JSON fetch()
#    endpoint, not the classic CSRF target: the browser blocks cross-site
#    requests carrying an application/json body before they reach the
#    server, and those routes rely on SESSION_COOKIE_SAMESITE=Lax instead
#    (see app.py). The SSLCommerz IPN/callback routes specifically are also
#    posted to by SSLCommerz's own servers rather than the user's browser,
#    and are separately protected by server-to-server amount/signature
#    validation (see payment_routes.py::_ssl_callback).
#  - /health is a liveness probe with no session/user context.
EXEMPT_PREFIXES = ("/api/", "/health")


def register_csrf_protection(app):
    @app.before_request
    def _check_csrf():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        if request.path.startswith(EXEMPT_PREFIXES):
            return
        # Only the traditional form body is checked here — JSON bodies go
        # through the exempt API prefixes above.
        submitted = request.form.get("csrf_token")
        if not _valid_csrf_token(submitted):
            abort(400, description="Invalid or missing CSRF token. Please refresh the page and try again.")

    @app.context_processor
    def _inject_csrf_token():
        return {"csrf_token": generate_csrf_token}
