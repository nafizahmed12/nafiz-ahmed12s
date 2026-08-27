import hmac
import os
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


ADMIN_ROLE = "admin"


def _configured_admin_username():
    return os.getenv("ADMIN_USERNAME", "").strip()


def admin_required(view):
    """Require a valid admin session bound to the configured owner account."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        configured_username = _configured_admin_username()
        session_username = str(session.get("admin_username", "")).strip()
        authenticated = (
            bool(configured_username)
            and session.get("admin_logged_in") is True
            and session.get("admin_role") == ADMIN_ROLE
            and bool(session_username)
            and hmac.compare_digest(session_username, configured_username)
        )
        if not authenticated:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
