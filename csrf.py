import hmac
import secrets
from urllib.parse import urlparse

from flask import abort, request, session


def _get_or_create_csrf_secret():
    """Per-session random value the token is bound to."""
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


def _valid_same_origin_request():
    """Validate browser origin metadata for state-changing JSON API calls.

    API endpoints use JSON fetch() rather than traditional HTML forms, so a
    form token is not always available. Origin/Referer validation prevents a
    cross-site browser from using the victim's session cookie to perform a
    state-changing API request. Requests without these headers remain
    compatible with server-to-server integrations and CLI clients.
    """
    expected_origin = request.host_url.rstrip("/")

    origin = request.headers.get("Origin")
    if origin:
        parsed = urlparse(origin)
        actual_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return hmac.compare_digest(actual_origin, expected_origin)

    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        actual_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return hmac.compare_digest(actual_origin, expected_origin)

    return True


# JSON API endpoints use same-origin browser validation instead of requiring
# an HTML form token. External payment callbacks are also under /api/ and may
# not send Origin/Referer; they have their own server-side signature/amount
# validation in payment_routes.py.
EXEMPT_PREFIXES = ("/api/", "/health")


def register_csrf_protection(app):
    @app.before_request
    def _check_csrf():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return

        # SSLCommerz browser callbacks originate from the external gateway,
        # so their Origin/Referer is intentionally not the merchant origin.
        # These endpoints perform their own server-side transaction validation.
        if request.path.startswith("/api/payments/sslcommerz/"):
            return

        if request.path.startswith("/api/"):
            if not _valid_same_origin_request():
                abort(400, description="Cross-origin API request blocked.")
            return

        if request.path.startswith("/health"):
            return

        submitted = request.form.get("csrf_token")
        if not _valid_csrf_token(submitted):
            abort(400, description="Invalid or missing CSRF token. Please refresh the page and try again.")

    @app.context_processor
    def _inject_csrf_token():
        # Templates expect csrf_token to be the actual string value.
        return {"csrf_token": generate_csrf_token()}
