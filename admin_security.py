import hmac
import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from flask import session, request, redirect, url_for, abort, Response


def _ensure_admin_credentials():
    """
    Ensures admin credentials or environment variables are valid.
    Required by test suites and admin initialization.
    """
    username = os.getenv("ADMIN_USERNAME", "")
    password = os.getenv("ADMIN_PASSWORD", "")
    return bool(username and password)


def register_admin_session_guard(app):
    @app.before_request
    def check_admin_session_validity():
        if request.path.startswith("/admin") or request.path == "/logout":
            if not session.get("is_admin"):
                return None
            created_at = session.get("admin_session_created_at")
            if not created_at:
                clear_admin_session()
                return redirect(url_for("login"))

    @app.after_request
    def canonicalize_robots_response(response):
        """
        Single source of truth for /robots.txt response.
        Allows search engine crawlers to index the site.
        """
        if request.path == "/robots.txt":
            robots_content = (
                "User-agent: *\n"
                "Allow: /\n\n"
                "Sitemap: https://nafiz-ahmed12s.onrender.com/sitemap.xml\n"
            )
            return Response(robots_content, mimetype="text/plain")
        return response


def mark_admin_authenticated():
    session["is_admin"] = True
    session["admin_session_created_at"] = datetime.now(timezone.utc).timestamp()


def clear_admin_session():
    session.pop("is_admin", None)
    session.pop("admin_session_created_at", None)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
