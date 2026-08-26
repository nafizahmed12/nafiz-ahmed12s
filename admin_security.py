import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import redirect, session, url_for, request, render_template
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from database import SessionLocal
from admin_product_routes import register_admin_product_routes
from supplier_auth_routes import register_supplier_auth_routes
from home_routes import register_home_routes
from admin_auth import ADMIN_ROLE


ADMIN_IDLE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", "1800"))
ADMIN_ABSOLUTE_TIMEOUT_SECONDS = int(os.getenv("ADMIN_ABSOLUTE_TIMEOUT_SECONDS", "43200"))
USER_SESSION_CREATED_KEY = "user_session_created_at"


def _ensure_admin_credentials():
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not username or not password or not email:
        return
    with SessionLocal() as db:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_credentials (
                id INTEGER PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                password_changed_at TIMESTAMP WITH TIME ZONE NULL
            )
        """))
        row = db.execute(text("SELECT id FROM admin_credentials LIMIT 1")).first()
        if row is None:
            db.execute(text("""INSERT INTO admin_credentials
                (id, username, email, password_hash)
                VALUES (1, :username, :email, :password_hash)"""), {
                "username": username,
                "email": email,
                "password_hash": generate_password_hash(password),
            })
        db.commit()


def register_admin_session_guard(app):
    """Register privileged-session guards and public/admin password-reset routes."""
    register_admin_product_routes(app)
    register_supplier_auth_routes(app)
    register_home_routes(app)
    register_password_reset_routes(app)
    _ensure_admin_credentials()

    @app.before_request
    def handle_admin_login_from_db():
        """Use the DB credential so a reset password takes effect immediately."""
        if request.path != "/login" or request.method != "POST":
            return None
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return None
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT username, password_hash FROM admin_credentials WHERE username=:username LIMIT 1"),
                {"username": username},
            ).mappings().first()
        if row is None:
            return None
        if not check_password_hash(row["password_hash"], password):
            return "Invalid username or password.", 401
        session.clear()
        session.permanent = True
        mark_admin_authenticated()
        return redirect(url_for("admin"))

    @app.before_request
    def guard_admin_session():
        if not session.get("admin_logged_in"):
            return None
        if session.get("admin_role") != ADMIN_ROLE:
            _clear_admin_session()
            return redirect(url_for("login"))
        now = datetime.now(timezone.utc).timestamp()
        authenticated_at = session.get("admin_authenticated_at")
        last_activity = session.get("admin_last_activity")
        if authenticated_at is None or last_activity is None:
            _clear_admin_session()
            return redirect(url_for("login"))
        try:
            authenticated_at = float(authenticated_at)
            last_activity = float(last_activity)
        except (TypeError, ValueError):
            _clear_admin_session()
            return redirect(url_for("login"))
        if now - authenticated_at > ADMIN_ABSOLUTE_TIMEOUT_SECONDS or now - last_activity > ADMIN_IDLE_TIMEOUT_SECONDS:
            _clear_admin_session()
            return redirect(url_for("login"))
        session["admin_last_activity"] = now
        return None

    @app.before_request
    def guard_user_session():
        """Revoke every user session created before the latest password change."""
        user_id = session.get("user_id")
        if not user_id or session.get("admin_logged_in"):
            return None
        created_at = session.get(USER_SESSION_CREATED_KEY)
        try:
            created_ts = float(created_at) if created_at is not None else None
        except (TypeError, ValueError):
            created_ts = None
        if created_ts is None:
            session.clear()
            return redirect(url_for("user_login"))
        with SessionLocal() as db:
            changed_at = db.execute(text("SELECT password_changed_at FROM users WHERE id=:uid"), {"uid": user_id}).scalar_one_or_none()
        if changed_at is not None:
            if changed_at.tzinfo is None:
                changed_at = changed_at.replace(tzinfo=timezone.utc)
            if created_ts < changed_at.timestamp():
                session.clear()
                return redirect(url_for("user_login"))
        return None

    @app.after_request
    def attach_home_javascript(response):
        if request.path == "/" and response.status_code == 200 and "text/html" in response.content_type:
            body = response.get_data(as_text=True)
            marker = '<script src="/static/home.js" defer></script>'
            if marker not in body and "</body>" in body:
                body = body.replace("</body>", marker + "</body>")
                response.set_data(body)
        return response


def register_password_reset_routes(app):
    """Register public user recovery and secure admin recovery endpoints."""
    if "forgot_password" not in app.view_functions:
        @app.route("/forgot-password", methods=["GET", "POST"])
        def forgot_password():
            if request.method == "GET":
                return render_template("forgot_password.html", sent=False)
            identifier = request.form.get("identifier", "").strip()
            import app as app_module
            if not app_module.allow_password_reset(request.remote_addr, identifier, limit=5, window_seconds=900):
                return render_template("forgot_password.html", sent=False, error="Too many reset attempts. Please try again later."), 429
            token, email = app_module.create_password_reset_token(identifier)
            if token and email:
                try:
                    app_module.send_password_reset_email(email, token)
                except Exception:
                    app.logger.exception("Password reset email delivery failed")
            return render_template("forgot_password.html", sent=True), 200

    if "reset_password" not in app.view_functions:
        @app.route("/reset-password", methods=["GET", "POST"])
        def reset_password():
            token = request.args.get("token", "").strip() if request.method == "GET" else request.form.get("token", "").strip()
            if request.method == "GET":
                return render_template("reset_password.html", token=token, error=None)
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            if password != confirm_password:
                return render_template("reset_password.html", token=token, error="Passwords do not match."), 400
            if len(password) < 8:
                return render_template("reset_password.html", token=token, error="Password must be at least 8 characters."), 400
            import app as app_module
            if app_module.reset_password_with_token(token, password):
                session.clear()
                return redirect(url_for("user_login"))
            return render_template("reset_password.html", token=token, error="This reset link is invalid or expired."), 400

    # Guard admin routes as well so this registration function is idempotent.
    if "admin_forgot_password" not in app.view_functions:
        @app.route("/admin-forgot-password", methods=["GET", "POST"])
        def admin_forgot_password():
            if request.method == "GET":
                return render_template("admin_forgot_password.html", sent=False)
            identifier = request.form.get("identifier", "").strip().lower()
            allowed = os.getenv("ADMIN_EMAIL", "").strip().lower()
            if not allowed or not hmac.compare_digest(identifier, allowed):
                return render_template("admin_forgot_password.html", sent=True)
            now = datetime.now(timezone.utc)
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            with SessionLocal() as db:
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS admin_password_reset_tokens (
                        token_hash VARCHAR(64) PRIMARY KEY,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        used_at TIMESTAMP WITH TIME ZONE NULL
                    )
                """))
                db.execute(text("DELETE FROM admin_password_reset_tokens WHERE expires_at <= :now OR used_at IS NOT NULL"), {"now": now})
                db.execute(text("INSERT INTO admin_password_reset_tokens (token_hash, expires_at) VALUES (:hash, :expires)"), {"hash": token_hash, "expires": now + timedelta(minutes=30)})
                db.commit()
            try:
                from mail_utils import send_admin_password_reset_email
                send_admin_password_reset_email(allowed, token)
            except Exception:
                app.logger.exception("Admin password reset email delivery failed")
            return render_template("admin_forgot_password.html", sent=True)

    if "admin_reset_password" not in app.view_functions:
        @app.route("/admin-reset-password", methods=["GET", "POST"])
        def admin_reset_password():
            token = request.args.get("token", "").strip() if request.method == "GET" else request.form.get("token", "").strip()
            if request.method == "GET":
                return render_template("admin_reset_password.html", token=token, error=None)
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if len(password) < 8:
                return render_template("admin_reset_password.html", token=token, error="Password must be at least 8 characters."), 400
            if password != confirm:
                return render_template("admin_reset_password.html", token=token, error="Passwords do not match."), 400
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            now = datetime.now(timezone.utc)
            with SessionLocal() as db:
                claimed = db.execute(text("""
                    UPDATE admin_password_reset_tokens
                    SET used_at=:now
                    WHERE token_hash=:hash AND used_at IS NULL AND expires_at > :now
                """), {"hash": token_hash, "now": now}).rowcount
                if claimed != 1:
                    db.rollback()
                    return render_template("admin_reset_password.html", token=token, error="This reset link is invalid or expired."), 400
                db.execute(text("UPDATE admin_credentials SET password_hash=:password_hash, password_changed_at=:now WHERE id=1"), {"password_hash": generate_password_hash(password), "now": now})
                db.commit()
            session.clear()
            return redirect(url_for("login"))


def mark_admin_authenticated():
    now = datetime.now(timezone.utc).timestamp()
    session["admin_logged_in"] = True
    session["admin_role"] = ADMIN_ROLE
    session["admin_authenticated_at"] = now
    session["admin_last_activity"] = now


def clear_admin_session():
    _clear_admin_session()


def _clear_admin_session():
    session.pop("admin_logged_in", None)
    session.pop("admin_role", None)
    session.pop("admin_authenticated_at", None)
    session.pop("admin_last_activity", None)
    session.pop("_permanent", None)
