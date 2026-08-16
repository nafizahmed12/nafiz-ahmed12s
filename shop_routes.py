from flask import Blueprint, render_template, session

shop_bp = Blueprint("shop_ui", __name__)


@shop_bp.get("/shop")
def shop():
    return render_template("shop.html")


@shop_bp.get("/checkout")
def checkout_page():
    if not session.get("user_id"):
        return render_template("shop.html", checkout_requires_login=True), 401
    return render_template("shop.html", checkout_mode=True)


def register_shop_routes(app):
    if shop_bp.name not in app.blueprints:
        app.register_blueprint(shop_bp)
