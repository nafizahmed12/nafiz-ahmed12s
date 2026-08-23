from functools import wraps

from flask import jsonify, redirect, request, session, url_for


ADMIN_ROLE = "admin"


def admin_required(view):
    """Require an authenticated session with the explicit admin role."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in") or session.get("admin_role") != ADMIN_ROLE:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
