import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import jsonify, redirect, session, url_for, request, render_template
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
    """Create/sync the bootstrap admin from environment variables.

    This is intentionally idempotent so it is safe to run on every deployment.
    ADMIN_EMAIL is optional because admin login only requires username/password.
    """
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    email = os.getenv("ADMIN_EMAIL", "").strip().lower() or None
    if not username or not password:
        return
    with SessionLocal() as db:
        db.execute(text("""CREATE TABLE IF NOT EXISTS admin_credentials (
            id INTEGER PRIMARY KEY, username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE, password_hash VARCHAR(255) NOT NULL,
            password_changed_at TIMESTAMP WITH TIME ZONE NULL)"""))
        row = db.execute(text("SELECT id, username, email FROM admin_credentials ORDER BY id LIMIT 1")).mappings().first()
        if row is None:
            db.execute(text("""INSERT INTO admin_credentials
                (id, username, email, password_hash) VALUES (1, :username, :email, :password_hash)"""),
                {"username": username, "email": email, "password_hash": generate_password_hash(password)})
        elif row["username"] != username or (email and row["email"] != email):
            db.execute(text("""UPDATE admin_credentials
                SET username=:username, email=:email
                WHERE id=:id"""),
                {"username": username, "email": email if email else row["email"], "id": row["id"]})
        db.commit()


def register_admin_session_guard(app):
    register_admin_product_routes(app)
    register_supplier_auth_routes(app)
    register_home_routes(app)
    register_password_reset_routes(app)
    _ensure_admin_credentials()

    @app.before_request
    def handle_admin_login_from_db():
        if request.path != "/login" or request.method != "POST":
            return None
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return None
        with SessionLocal() as db:
            row = db.execute(text("SELECT username, password_hash FROM admin_credentials WHERE username=:username LIMIT 1"), {"username": username}).mappings().first()
        if row is None:
            return None
        if not check_password_hash(row["password_hash"], password):
            return "Invalid username or password.", 401
        session.clear(); session.permanent = True; mark_admin_authenticated(row["username"])
        return redirect(url_for("admin"))

    @app.before_request
    def guard_admin_session():
        if not session.get("admin_logged_in"):
            return None

        def reject_admin_session():
            _clear_admin_session()
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("login"))

        if session.get("admin_role") != ADMIN_ROLE:
            return reject_admin_session()
        configured_username = os.getenv("ADMIN_USERNAME", "").strip()
        session_username = str(session.get("admin_username", "")).strip()
        if not configured_username or not session_username or not hmac.compare_digest(session_username, configured_username):
            return reject_admin_session()
        now = datetime.now(timezone.utc).timestamp()
        try:
            authenticated_at = float(session.get("admin_authenticated_at")); last_activity = float(session.get("admin_last_activity"))
        except (TypeError, ValueError):
            return reject_admin_session()
        if now - authenticated_at > ADMIN_ABSOLUTE_TIMEOUT_SECONDS or now - last_activity > ADMIN_IDLE_TIMEOUT_SECONDS:
            return reject_admin_session()
        session["admin_last_activity"] = now

    @app.before_request
    def guard_user_session():
        user_id = session.get("user_id")
        if not user_id or session.get("admin_logged_in"):
            return None
        try:
            created_ts = float(session.get(USER_SESSION_CREATED_KEY))
        except (TypeError, ValueError):
            session.clear(); return redirect(url_for("user_login"))
        with SessionLocal() as db:
            changed_at = db.execute(text("SELECT password_changed_at FROM users WHERE id=:uid"), {"uid": user_id}).scalar_one_or_none()
        if changed_at is not None:
            if changed_at.tzinfo is None: changed_at = changed_at.replace(tzinfo=timezone.utc)
            if created_ts < changed_at.timestamp():
                session.clear(); return redirect(url_for("user_login"))

    @app.after_request
    def attach_home_javascript(response):
        if request.path == "/" and response.status_code == 200 and "text/html" in response.content_type:
            body = response.get_data(as_text=True)
            marker = '<script src="/static/home.js" defer></script>'
            if marker not in body and "</body>" in body:
                response.set_data(body.replace("</body>", marker + "</body>"))
        return response


def register_password_reset_routes(app):
    if "forgot_password" not in app.view_functions:
        @app.route("/forgot-password", methods=["GET", "POST"])
        def forgot_password():
            if request.method == "GET": return render_template("forgot_password.html", sent=False)
            identifier = request.form.get("identifier", "").strip()
            import app as app_module
            if not app_module.allow_password_reset(request.remote_addr, identifier, limit=5, window_seconds=900):
                return render_template("forgot_password.html", sent=False, error="Too many reset attempts. Please try again later."), 429
            token, email = app_module.create_password_reset_token(identifier)
            sent = False
            if token and email:
                try:
                    app_module.send_password_reset_email(email, token); sent = True
                except Exception:
                    app.logger.exception("Password reset email delivery failed")
            return render_template("forgot_password.html", sent=sent, error=None if sent else "We could not send the reset email. Please check your email configuration and try again."), 200

    if "reset_password" not in app.view_functions:
        @app.route("/reset-password", methods=["GET", "POST"])
        def reset_password():
            token = request.args.get("token", "").strip() if request.method == "GET" else request.form.get("token", "").strip()
            if request.method == "GET": return render_template("reset_password.html", token=token, error=None)
            password = request.form.get("password", ""); confirm = request.form.get("confirm_password", "")
            if password != confirm: return render_template("reset_password.html", token=token, error="Passwords do not match."), 400
            if len(password) < 8: return render_template("reset_password.html", token=token, error="Password must be at least 8 characters."), 400
            import app as app_module
            if app_module.reset_password_with_token(token, password):
                session.clear(); return redirect(url_for("user_login"))
            return render_template("reset_password.html", token=token, error="This reset link is invalid or expired."), 400

    if "admin_forgot_password" not in app.view_functions:
        @app.route("/admin-forgot-password", methods=["GET", "POST"])
        def admin_forgot_password():
            if request.method == "GET": return render_template("admin_forgot_password.html", sent=False)
            identifier = request.form.get("identifier", "").strip().lower()
            allowed = os.getenv("ADMIN_EMAIL", "").strip().lower()
            if not allowed or not hmac.compare_digest(identifier, allowed):
                return render_template("admin_forgot_password.html", sent=False, error="If that email is registered, a reset link will be sent."), 200
            now = datetime.now(timezone.utc); token = secrets.token_urlsafe(32); token_hash = hashlib.sha256(token.encode()).hexdigest()
            with SessionLocal() as db:
                db.execute(text("""CREATE TABLE IF NOT EXISTS admin_password_reset_tokens (
                    token_hash VARCHAR(64) PRIMARY KEY, expires_at TIMESTAMP WITH TIME ZONE NOT NULL, used_at TIMESTAMP WITH TIME ZONE NULL)"""))
                db.execute(text("DELETE FROM admin_password_reset_tokens WHERE expires_at <= :now OR used_at IS NOT NULL"), {"now": now})
                db.execute(text("INSERT INTO admin_password_reset_tokens (token_hash, expires_at) VALUES (:hash, :expires)"), {"hash": token_hash, "expires": now + timedelta(minutes=30)})
                db.commit()
            from mail_utils import send_admin_password_reset_email
            try:
                send_admin_password_reset_email(allowed, token)
            except Exception:
                app.logger.exception("Admin password reset email delivery failed")
                return render_template("admin_forgot_password.html", sent=False, error="We could not send the reset email. Please check the email configuration."), 200
            return render_template("admin_forgot_password.html", sent=True, error=None), 200

    if "admin_reset_password" not in app.view_functions:
        @app.route("/admin-reset-password", methods=["GET", "POST"])
        def admin_reset_password():
            token = request.args.get("token", "").strip() if request.method == "GET" else request.form.get("token", "").strip()
            if request.method == "GET": return render_template("admin_reset_password.html", token=token, error=None)
            password = request.form.get("password", ""); confirm = request.form.get("confirm_password", "")
            if len(password) < 8: return render_template("admin_reset_password.html", token=token, error="Passwords do not match."), 400
            if password != confirm: return render_template("admin_reset_password.html", token=token, error="Passwords do not match."), 400
            token_hash = hashlib.sha256(token.encode()).hexdigest(); now = datetime.now(timezone.utc)
            with SessionLocal() as db:
                claimed = db.execute(text("UPDATE admin_password_reset_tokens SET used_at=:now WHERE token_hash=:hash AND used_at IS NULL AND expires_at > :now"), {"hash": token_hash, "now": now}).rowcount
                if claimed != 1:
                    db.rollback(); return render_template("admin_reset_password.html", token=token, error="This reset link is invalid or expired."), 400
                db.execute(text("UPDATE admin_credentials SET password_hash=:password_hash, password_changed_at=:now WHERE id=1"), {"password_hash": generate_password_hash(password), "now": now}); db.commit()
            session.clear(); return redirect(url_for("login"))


def mark_admin_authenticated(username):
    configured_username = os.getenv("ADMIN_USERNAME", "").strip()
    if not configured_username or not username or not hmac.compare_digest(str(username).strip(), configured_username):
        raise ValueError("Configured admin identity mismatch.")
    now = datetime.now(timezone.utc).timestamp()
    session["admin_logged_in"] = True; session["admin_role"] = ADMIN_ROLE
    session["admin_username"] = configured_username
    session["admin_authenticated_at"] = now; session["admin_last_activity"] = now


def clear_admin_session(): _clear_admin_session()


def _clear_admin_session():
    session.pop("admin_logged_in", None); session.pop("admin_role", None)
    session.pop("admin_username", None); session.pop("admin_authenticated_at", None); session.pop("admin_last_activity", None); session.pop("_permanent", None)
