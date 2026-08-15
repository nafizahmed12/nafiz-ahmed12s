import os
from datetime import datetime, timezone

from flask import redirect, session, url_for


ADMIN_IDLE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", "1800"))
ADMIN_ABSOLUTE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200"))


def register_admin_session_guard(app):
    """Expire privileged admin sessions after idle/absolute time limits."""

    @app.before_request
    def guard_admin_session():
        if not session.get("admin_logged_in"):
            return None

        now = datetime.now(timezone.utc).timestamp()
        authenticated_at = session.get("admin_authenticated_at")
        last_activity = session.get("admin_last_activity")

        # Sessions created before this hardening release do not have timestamps.
        # Initialize them once so an already-authenticated admin is not logged out
        # unexpectedly during deployment.
        if authenticated_at is None or last_activity is None:
            session["admin_authenticated_at"] = now
            session["admin_last_activity"] = now
            return None

        try:
            authenticated_at = float(authenticated_at)
            last_activity = float(last_activity)
        except (TypeError, ValueError):
            _clear_admin_session()
            return redirect(url_for("login"))

        if (
            now - authenticated_at > ADMIN_ABSOLUTE_TIMEOUT_SECONDS
            or now - last_activity > ADMIN_IDLE_TIMEOUT_SECONDS
        ):
            _clear_admin_session()
            return redirect(url_for("login"))

        session["admin_last_activity"] = now
        return None


def mark_admin_authenticated():
    """Initialize timestamps for a newly authenticated admin session."""
    now = datetime.now(timezone.utc).timestamp()
    session["admin_logged_in"] = True
    session["admin_authenticated_at"] = now
    session["admin_last_activity"] = now


def clear_admin_session():
    """Public helper for explicitly terminating the privileged session."""
    _clear_admin_session()


def _clear_admin_session():
    session.pop("admin_logged_in", None)
    session.pop("admin_authenticated_at", None)
    session.pop("admin_last_activity", None)
    session.pop("_permanent", None)
