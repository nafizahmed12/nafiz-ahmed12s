"""Supplier registration, login and dashboard pages."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from database import SessionLocal
from schema import create_user, authenticate_user

supplier_auth_bp = Blueprint("supplier_auth", __name__)


def register_supplier_auth_routes(app):
    if supplier_auth_bp.name not in app.blueprints:
        app.register_blueprint(supplier_auth_bp)


def _supplier_profile_for_user(user_id):
    with SessionLocal() as db:
        return db.execute(
            text("SELECT id, status FROM supplier_profiles WHERE user_id=:uid"),
            {"uid": user_id},
        ).mappings().first()


def _create_supplier_profile(user_id, company, email, phone, country):
    """Create a supplier profile for an existing user."""
    slug = "".join(c.lower() if c.isalnum() else "-" for c in company).strip("-")[:190]
    slug = slug or f"supplier-{user_id}"

    with SessionLocal() as db:
        if db.execute(
            text("SELECT 1 FROM supplier_profiles WHERE user_id=:uid LIMIT 1"),
            {"uid": user_id},
        ).first():
            return False, "This account is already registered as a supplier."

        if db.execute(
            text("SELECT 1 FROM supplier_profiles WHERE slug=:slug LIMIT 1"),
            {"slug": slug},
        ).first():
            slug = f"{slug}-{user_id}"

        try:
            db.execute(
                text("""INSERT INTO supplier_profiles
                    (user_id, company_name, slug, description, status, contact_email,
                     contact_phone, country, created_at, updated_at)
                    VALUES (:uid,:company,:slug,'','pending',:email,:phone,:country,NOW(),NOW())"""),
                {
                    "uid": user_id,
                    "company": company,
                    "slug": slug,
                    "email": email,
                    "phone": phone,
                    "country": country,
                },
            )
            db.commit()
            return True, "Supplier account created. Your account is pending approval."
        except IntegrityError:
            db.rollback()
            return False, "This supplier account could not be created. Please try again."


@supplier_auth_bp.route("/supplier/register", methods=["GET", "POST"])
def supplier_register_page():
    # Existing normal users can become suppliers instead of being redirected
    # away from the registration page. Existing suppliers still go to dashboard.
    logged_in_user_id = session.get("user_id")
    if logged_in_user_id and _supplier_profile_for_user(logged_in_user_id):
        return redirect(url_for("supplier_auth.supplier_dashboard_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company = request.form.get("company_name", "").strip()
        phone = request.form.get("phone", "").strip()
        country = request.form.get("country", "Bangladesh").strip() or "Bangladesh"
        form_data = {
            "company_name": company,
            "username": username,
            "email": email,
            "phone": phone,
            "country": country,
        }

        if len(username) < 3 or len(username) > 80 or len(password) < 8 or not company or not email:
            return render_template(
                "supplier_register.html",
                error="Username, email, company name and password (8+ chars) are required.",
                form_data=form_data,
            ), 400

        # Logged-in users can create a supplier profile on their existing account.
        if logged_in_user_id:
            with SessionLocal() as db:
                existing_user = db.execute(
                    text("SELECT id, username, email, password_hash FROM users WHERE id=:uid"),
                    {"uid": logged_in_user_id},
                ).mappings().first()

            if existing_user is None:
                session.clear()
                return render_template(
                    "supplier_register.html",
                    error="Your login session is no longer valid. Please log in again.",
                    form_data=form_data,
                ), 401

            if existing_user["username"] != username or existing_user["email"] != email:
                return render_template(
                    "supplier_register.html",
                    error="For your existing account, username and email must match your account details.",
                    form_data=form_data,
                ), 409

            if not check_password_hash(existing_user["password_hash"], password):
                return render_template(
                    "supplier_register.html",
                    error="Your current account password is incorrect.",
                    form_data=form_data,
                ), 401

            ok, message = _create_supplier_profile(
                existing_user["id"], company, email, phone, country
            )
            if not ok:
                return render_template(
                    "supplier_register.html", error=message, form_data=form_data
                ), 409

            session["user_id"] = existing_user["id"]
            session["username"] = existing_user["username"]
            flash(message, "success")
            return redirect(url_for("supplier_auth.supplier_dashboard_page"))

        # No active session: if username and email belong to the same existing
        # account, allow that account to become a supplier after password check.
        with SessionLocal() as db:
            existing_username = db.execute(
                text("SELECT id, username, email, password_hash FROM users WHERE username=:username LIMIT 1"),
                {"username": username},
            ).mappings().first()
            existing_email = db.execute(
                text("SELECT id, username, email, password_hash FROM users WHERE email=:email LIMIT 1"),
                {"email": email},
            ).mappings().first()

        if existing_username and existing_email and existing_username["id"] == existing_email["id"]:
            existing_user = existing_username
            if not check_password_hash(existing_user["password_hash"], password):
                return render_template(
                    "supplier_register.html",
                    error="This username/email already belongs to an account. Enter that account's password to become a supplier.",
                    form_data=form_data,
                ), 409

            if _supplier_profile_for_user(existing_user["id"]):
                return render_template(
                    "supplier_register.html",
                    error="This account is already registered as a supplier. Use Supplier login.",
                    form_data=form_data,
                ), 409

            ok, message = _create_supplier_profile(
                existing_user["id"], company, email, phone, country
            )
            if not ok:
                return render_template(
                    "supplier_register.html", error=message, form_data=form_data
                ), 409

            session.clear()
            session.permanent = True
            session["user_id"] = existing_user["id"]
            session["username"] = existing_user["username"]
            flash(message, "success")
            return redirect(url_for("supplier_auth.supplier_dashboard_page"))

        if existing_username:
            return render_template(
                "supplier_register.html",
                error="This username is already in use. Keep your existing username and email together, or choose a different username.",
                form_data=form_data,
            ), 409
        if existing_email:
            return render_template(
                "supplier_register.html",
                error="This email is already registered. Use that account's username too, or choose a different email.",
                form_data=form_data,
            ), 409

        user = create_user(username, email, password)
        if user is None:
            # Re-check after a concurrent INSERT to avoid a misleading message.
            with SessionLocal() as db:
                username_exists = db.execute(
                    text("SELECT 1 FROM users WHERE username=:username LIMIT 1"),
                    {"username": username},
                ).first()
                email_exists = db.execute(
                    text("SELECT 1 FROM users WHERE email=:email LIMIT 1"),
                    {"email": email},
                ).first()
            if username_exists and email_exists:
                message = "Both username and email are already in use. If this is your account, enter its correct password with the same username and email."
            elif username_exists:
                message = "This username is already in use. Please choose a different username."
            elif email_exists:
                message = "This email is already registered. Please use a different email."
            else:
                message = "Registration could not be completed. Please try again."
            return render_template(
                "supplier_register.html", error=message, form_data=form_data
            ), 409

        ok, message = _create_supplier_profile(user.id, company, email, phone, country)
        if not ok:
            with SessionLocal() as db:
                db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": user.id})
                db.commit()
            return render_template(
                "supplier_register.html", error=message, form_data=form_data
            ), 409

        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["username"] = user.username
        flash(message, "success")
        return redirect(url_for("supplier_auth.supplier_dashboard_page"))

    form_data = {}
    if logged_in_user_id:
        with SessionLocal() as db:
            current_user = db.execute(
                text("SELECT username, email FROM users WHERE id=:uid"),
                {"uid": logged_in_user_id},
            ).mappings().first()
        if current_user:
            form_data = {
                "username": current_user["username"],
                "email": current_user["email"],
            }

    return render_template("supplier_register.html", form_data=form_data)


@supplier_auth_bp.route("/supplier/login", methods=["GET", "POST"])
def supplier_login_page():
    if session.get("user_id"):
        profile = _supplier_profile_for_user(session["user_id"])
        if profile:
            return redirect(url_for("supplier_auth.supplier_dashboard_page"))
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = authenticate_user(identifier, password)
        if user is None:
            return render_template("supplier_login.html", error="Invalid username/email or password."), 401
        profile = _supplier_profile_for_user(user.id)
        if profile is None:
            return render_template("supplier_login.html", error="This account is not registered as a supplier."), 403
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect(url_for("supplier_auth.supplier_dashboard_page"))
    return render_template("supplier_login.html")


@supplier_auth_bp.route("/supplier/dashboard")
def supplier_dashboard_page():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("supplier_auth.supplier_login_page"))
    with SessionLocal() as db:
        profile = db.execute(text("SELECT * FROM supplier_profiles WHERE user_id=:uid"), {"uid": user_id}).mappings().first()
        if profile is None:
            session.pop("user_id", None)
            session.pop("username", None)
            return redirect(url_for("supplier_auth.supplier_login_page"))
        orders = db.execute(text("""SELECT so.id, so.order_id, co.order_number, so.status,
            so.tracking_number, so.cost_total, so.created_at FROM supplier_orders so
            JOIN commerce_orders co ON co.id=so.order_id
            WHERE so.supplier_id=:sid ORDER BY so.id DESC"""), {"sid": profile["id"]}).mappings().all()
        products = db.execute(text("""SELECT sp.id, p.name, sp.supplier_sku, sp.cost_price,
            sp.supplier_stock, sp.fulfillment_time_days, sp.is_active FROM supplier_products sp
            JOIN products p ON p.id=sp.product_id WHERE sp.supplier_id=:sid ORDER BY sp.id DESC"""),
            {"sid": profile["id"]}).mappings().all()
    return render_template("supplier_dashboard.html", profile=profile, orders=orders, products=products)


@supplier_auth_bp.route("/supplier/logout")
def supplier_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("_permanent", None)
    return redirect(url_for("supplier_auth.supplier_login_page"))
