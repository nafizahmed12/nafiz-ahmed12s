import os
from datetime import datetime, timezone

from flask import redirect, session, url_for, request
from sqlalchemy import text

from database import SessionLocal
from admin_product_routes import register_admin_product_routes
from supplier_auth_routes import register_supplier_auth_routes
from home_routes import register_home_routes


ADMIN_IDLE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", "1800"))
ADMIN_ABSOLUTE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200"))
USER_SESSION_CREATED_KEY = "user_session_created_at"


def register_admin_session_guard(app):
    """Expire privileged admin sessions and revoke user sessions after password changes."""
    register_admin_product_routes(app)
    register_supplier_auth_routes(app)
    register_home_routes(app)

    @app.before_request
    def guard_admin_session():
        if not session.get("admin_logged_in"):
            return None

        now = datetime.now(timezone.utc).timestamp()
        authenticated_at = session.get("admin_authenticated_at")
        last_activity = session.get("admin_last_activity")

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

    @app.before_request
    def guard_user_session():
        """Bind each user session to its creation time and revoke it after a password change."""
        user_id = session.get("user_id")
        if not user_id or session.get("admin_logged_in"):
            return None

        now = datetime.now(timezone.utc)
        created_at = session.get(USER_SESSION_CREATED_KEY)

        try:
            created_ts = float(created_at) if created_at is not None else None
        except (TypeError, ValueError):
            created_ts = None

        with SessionLocal() as db:
            changed_at = db.execute(
                text("SELECT password_changed_at FROM users WHERE id=:uid"),
                {"uid": user_id},
            ).scalar_one_or_none()

        if changed_at is not None:
            if changed_at.tzinfo is None:
                changed_at = changed_at.replace(tzinfo=timezone.utc)
            if created_ts is not None and created_ts < changed_at.timestamp():
                session.clear()
                return redirect(url_for("user_login"))

        if created_ts is None:
            session[USER_SESSION_CREATED_KEY] = now.timestamp()

        return None

    @app.after_request
    def attach_home_javascript(response):
        """Load the commerce homepage enhancement without changing the existing template."""
        if request.path == "/" and response.status_code == 200 and "text/html" in response.content_type:
            body = response.get_data(as_text=True)
            marker = '<script src="/static/home.js" defer></script>'
            if marker not in body and "</body>" in body:
                body = body.replace("</body>", marker + "</body>")
                response.set_data(body)
        return response


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
