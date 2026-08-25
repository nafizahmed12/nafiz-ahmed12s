from flask import Blueprint, render_template, session, request

shop_bp = Blueprint("shop_ui", __name__)


@shop_bp.get("/shop")
def shop():
    return render_template("shop.html", category=request.args.get("category", "").strip().lower())


@shop_bp.get("/checkout")
def checkout_page():
    if not session.get("user_id"):
        return render_template("shop.html", checkout_requires_login=True), 401
    return render_template("shop.html", checkout_mode=True)


@shop_bp.get("/payment/success")
def payment_success():
    return render_template(
        "payment_result.html",
        result="success",
        order_id=request.args.get("order_id"),
    )


@shop_bp.get("/payment/fail")
def payment_fail():
    return render_template(
        "payment_result.html",
        result="fail",
        order_id=request.args.get("order_id"),
    )


@shop_bp.get("/payment/cancel")
def payment_cancel():
    return render_template(
        "payment_result.html",
        result="cancel",
        order_id=request.args.get("order_id"),
    )


def register_shop_routes(app):
    if shop_bp.name not in app.blueprints:
        app.register_blueprint(shop_bp)
