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


@shop_bp.get("/payment/success")
def payment_success():
    return render_template(
        "payment_result.html",
        title="Payment Successful",
        icon="✓",
        icon_bg="linear-gradient(135deg,#10b981,#059669)",
        message="Your payment has been verified successfully. Your order is now confirmed.",
    )


@shop_bp.get("/payment/fail")
def payment_fail():
    return render_template(
        "payment_result.html",
        title="Payment Failed",
        icon="!",
        icon_bg="linear-gradient(135deg,#ef4444,#b91c1c)",
        message="We could not complete the payment. You can return to the shop and try again.",
    )


@shop_bp.get("/payment/cancel")
def payment_cancel():
    return render_template(
        "payment_result.html",
        title="Payment Cancelled",
        icon="×",
        icon_bg="linear-gradient(135deg,#f59e0b,#d97706)",
        message="The payment was cancelled. Your order was not marked as paid.",
    )


def register_shop_routes(app):
    if shop_bp.name not in app.blueprints:
        app.register_blueprint(shop_bp)
