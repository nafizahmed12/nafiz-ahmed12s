"""Supplier registration, login and dashboard pages."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from database import SessionLocal
from schema import create_user, authenticate_user

supplier_auth_bp = Blueprint("supplier_auth", __name__)


def register_supplier_auth_routes(app):
    if supplier_auth_bp.name not in app.blueprints:
        app.register_blueprint(supplier_auth_bp)


@supplier_auth_bp.route("/supplier/register", methods=["GET", "POST"])
def supplier_register_page():
    if session.get("user_id"):
        return redirect(url_for("supplier_dashboard_page"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company = request.form.get("company_name", "").strip()
        phone = request.form.get("phone", "").strip()
        country = request.form.get("country", "Bangladesh").strip() or "Bangladesh"
        if len(username) < 3 or len(username) > 80 or len(password) < 8 or not company:
            return render_template("supplier_register.html", error="Username, company name and password (8+ chars) are required."), 400
        user = create_user(username, email, password)
        if user is None:
            return render_template("supplier_register.html", error="Username or email is already in use."), 409
        slug = "".join(c.lower() if c.isalnum() else "-" for c in company).strip("-")[:190] or f"supplier-{user.id}"
        with SessionLocal() as db:
            if db.execute(text("SELECT 1 FROM supplier_profiles WHERE slug=:slug"), {"slug": slug}).first():
                slug = f"{slug}-{user.id}"
            db.execute(text("""INSERT INTO supplier_profiles
                (user_id, company_name, slug, description, status, contact_email, contact_phone, country, created_at, updated_at)
                VALUES (:uid,:company,:slug,'','pending',:email,:phone,:country,NOW(),NOW())"""),
                {"uid": user.id, "company": company, "slug": slug, "email": email, "phone": phone, "country": country})
            db.commit()
        session.clear(); session.permanent = True; session["user_id"] = user.id; session["username"] = user.username
        flash("Supplier account created. Your account is pending approval.", "success")
        return redirect(url_for("supplier_dashboard_page"))
    return render_template("supplier_register.html")


@supplier_auth_bp.route("/supplier/login", methods=["GET", "POST"])
def supplier_login_page():
    if session.get("user_id"):
        return redirect(url_for("supplier_dashboard_page"))
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = authenticate_user(identifier, password)
        if user is None:
            return render_template("supplier_login.html", error="Invalid username/email or password."), 401
        with SessionLocal() as db:
            profile = db.execute(text("SELECT id, status FROM supplier_profiles WHERE user_id=:uid"), {"uid": user.id}).mappings().first()
        if profile is None:
            return render_template("supplier_login.html", error="This account is not registered as a supplier."), 403
        session.clear(); session.permanent = True; session["user_id"] = user.id; session["username"] = user.username
        return redirect(url_for("supplier_dashboard_page"))
    return render_template("supplier_login.html")


@supplier_auth_bp.route("/supplier/dashboard")
def supplier_dashboard_page():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("supplier_login_page"))
    with SessionLocal() as db:
        profile = db.execute(text("SELECT * FROM supplier_profiles WHERE user_id=:uid"), {"uid": user_id}).mappings().first()
        if profile is None:
            session.pop("user_id", None); session.pop("username", None)
            return redirect(url_for("supplier_login_page"))
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
    session.pop("user_id", None); session.pop("username", None); session.pop("_permanent", None)
    return redirect(url_for("supplier_login_page"))
