import hmac
import os
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


ADMIN_ROLE = "admin"
ADMIN_IDLE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", "1800"))
ADMIN_ABSOLUTE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200"))


def _configured_admin_username():
    return os.getenv("ADMIN_USERNAME", "").strip()


def _valid_admin_session(configured_username):
    session_username = str(session.get("admin_username", "")).strip()
    if not (
        bool(configured_username)
        and session.get("admin_logged_in") is True
        and session.get("admin_role") == ADMIN_ROLE
        and bool(session_username)
        and hmac.compare_digest(session_username, configured_username)
    ):
        return False
    try:
        now = datetime.now(timezone.utc).timestamp()
        authenticated_at = float(session.get("admin_authenticated_at"))
        last_activity = float(session.get("admin_last_activity"))
    except (TypeError, ValueError):
        return False
    return (
        now - authenticated_at <= ADMIN_ABSOLUTE_TIMEOUT_SECONDS
        and now - last_activity <= ADMIN_IDLE_TIMEOUT_SECONDS
    )


def admin_required(view):
    """Require a valid admin session bound to the configured owner account."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        configured_username = _configured_admin_username()
        if not _valid_admin_session(configured_username):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
