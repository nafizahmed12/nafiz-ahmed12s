from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from schema import allow_cart_action, allow_checkout

commerce_bp = Blueprint("commerce_api", __name__, url_prefix="/api")


def _user_id():
    value = session.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _money(value):
    if value is None:
        return "0.00"
    return format(Decimal(str(value)), ".2f")


def _product_row(row):
    return {"id": row.id, "name": row.name, "slug": row.slug, "description": row.description or "", "product_type": row.product_type, "price": _money(row.price), "currency": row.currency, "sku": row.sku, "stock_quantity": row.stock_quantity, "image_url": row.image_url, "listing_id": row.listing_id, "listing_price": _money(row.listing_price) if row.listing_price is not None else None}


def _get_or_create_cart(db, user_id):
    cart_id = db.execute(text("SELECT id FROM carts WHERE user_id=:user_id"), {"user_id": user_id}).scalar_one_or_none()
    if cart_id is not None:
        return cart_id
    try:
        return db.execute(text("INSERT INTO carts (user_id,created_at,updated_at) VALUES (:user_id,NOW(),NOW()) RETURNING id"), {"user_id": user_id}).scalar_one()
    except IntegrityError:
        db.rollback()
        return db.execute(text("SELECT id FROM carts WHERE user_id=:user_id"), {"user_id": user_id}).scalar_one()


def _cart_payload(db, user_id):
    cart_id = _get_or_create_cart(db, user_id)
    rows = db.execute(text("""SELECT ci.id AS cart_item_id,ci.product_id,ci.quantity,p.name,p.slug,p.product_type,p.currency,p.stock_quantity,COALESCE(l.price,p.price) AS unit_price,pi.image_url FROM cart_items ci JOIN products p ON p.id=ci.product_id LEFT JOIN LATERAL (SELECT price FROM product_listings WHERE product_id=p.id AND status IN ('active','published') ORDER BY featured DESC,id ASC LIMIT 1) l ON TRUE LEFT JOIN LATERAL (SELECT image_url FROM product_images WHERE product_id=p.id ORDER BY sort_order ASC,id ASC LIMIT 1) pi ON TRUE WHERE ci.cart_id=:cart_id ORDER BY ci.id ASC"""), {"cart_id": cart_id}).mappings().all()
    items = []
    subtotal = Decimal("0")
    for row in rows:
        unit = Decimal(str(row["unit_price"] or 0))
        line = unit * row["quantity"]
        subtotal += line
        items.append({"cart_item_id": row["cart_item_id"], "product_id": row["product_id"], "name": row["name"], "slug": row["slug"], "product_type": row["product_type"], "quantity": row["quantity"], "unit_price": _money(unit), "line_total": _money(line), "currency": row["currency"], "stock_quantity": row["stock_quantity"], "image_url": row["image_url"]})
    return {"cart_id": cart_id, "items": items, "item_count": sum(i["quantity"] for i in items), "subtotal": _money(subtotal), "currency": items[0]["currency"] if items else "BDT"}


def _create_supplier_orders_for_order(db, order_id):
    """Create supplier fulfillment records for an order.

    Idempotent: existing supplier orders/items are reused, so payment callbacks
    or retries cannot create duplicate supplier orders.
    """
    rows = db.execute(text("""SELECT oi.id AS order_item_id,oi.quantity,oi.supplier_product_id,sp.supplier_id,sp.cost_price,sp.supplier_stock,sp.is_active
        FROM commerce_order_items oi
        LEFT JOIN supplier_products sp ON sp.id=oi.supplier_product_id
        WHERE oi.order_id=:order_id
        ORDER BY oi.id ASC"""), {"order_id": order_id}).mappings().all()

    created = 0
    skipped = []
    supplier_orders = {}

    for row in rows:
        supplier_product_id = row["supplier_product_id"]
        if supplier_product_id is None:
            continue
        if not row["is_active"] or row["supplier_id"] is None:
            skipped.append({"order_item_id": row["order_item_id"], "reason": "supplier_product_inactive_or_missing"})
            continue
        if row["supplier_stock"] < row["quantity"]:
            skipped.append({"order_item_id": row["order_item_id"], "reason": "insufficient_supplier_stock"})
            continue

        supplier_id = row["supplier_id"]
        supplier_order_id = supplier_orders.get(supplier_id)
        if supplier_order_id is None:
            supplier_order_id = db.execute(text("SELECT id FROM supplier_orders WHERE order_id=:order_id AND supplier_id=:supplier_id"), {"order_id": order_id, "supplier_id": supplier_id}).scalar_one_or_none()
            if supplier_order_id is None:
                supplier_order_id = db.execute(text("""INSERT INTO supplier_orders (order_id,supplier_id,status,external_order_ref,tracking_number,shipping_cost,cost_total,notes,created_at,updated_at)
                    VALUES (:order_id,:supplier_id,'pending',NULL,NULL,0,0,'Auto-created after successful customer order.',NOW(),NOW()) RETURNING id"""), {"order_id": order_id, "supplier_id": supplier_id}).scalar_one()
                created += 1
            supplier_orders[supplier_id] = supplier_order_id

        existing = db.execute(text("SELECT id FROM supplier_order_items WHERE supplier_order_id=:supplier_order_id AND order_item_id=:order_item_id"), {"supplier_order_id": supplier_order_id, "order_item_id": row["order_item_id"]}).scalar_one_or_none()
        if existing is not None:
            continue

        cost_price = Decimal(str(row["cost_price"] or 0))
        line_cost = cost_price * row["quantity"]
        db.execute(text("""INSERT INTO supplier_order_items (supplier_order_id,order_item_id,supplier_product_id,quantity,cost_price,line_cost)
            VALUES (:supplier_order_id,:order_item_id,:supplier_product_id,:quantity,:cost_price,:line_cost)"""), {"supplier_order_id": supplier_order_id, "order_item_id": row["order_item_id"], "supplier_product_id": supplier_product_id, "quantity": row["quantity"], "cost_price": cost_price, "line_cost": line_cost})
        db.execute(text("UPDATE supplier_orders SET cost_total=cost_total+:line_cost,updated_at=NOW() WHERE id=:supplier_order_id"), {"line_cost": line_cost, "supplier_order_id": supplier_order_id})
        db.execute(text("UPDATE supplier_products SET supplier_stock=supplier_stock-:quantity,updated_at=NOW() WHERE id=:supplier_product_id AND supplier_stock>=:quantity"), {"quantity": row["quantity"], "supplier_product_id": supplier_product_id})

    return {"created": created, "skipped": skipped, "supplier_order_ids": list(supplier_orders.values())}


@commerce_bp.get("/products")
def products():
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(50, max(1, int(request.args.get("per_page", "20"))))
    except ValueError:
        return jsonify({"error": "Invalid pagination."}), 400
    search = request.args.get("q", "").strip()
    product_type = request.args.get("type", "").strip().lower()
    offset = (page - 1) * per_page
    filters = ["p.status NOT IN ('draft', 'archived')"]
    params = {"limit": per_page, "offset": offset}
    if search:
        filters.append("(p.name ILIKE :search OR p.description ILIKE :search)")
        params["search"] = f"%{search}%"
    if product_type:
        filters.append("p.product_type = :product_type")
        params["product_type"] = product_type
    where_sql = " AND ".join(filters)
    with SessionLocal() as db:
        rows = db.execute(text(f"""SELECT p.id,p.name,p.slug,p.description,p.product_type,COALESCE(l.price,p.price) AS price,p.currency,p.sku,p.stock_quantity,pi.image_url,l.id AS listing_id,l.price AS listing_price FROM products p LEFT JOIN LATERAL (SELECT id,price FROM product_listings WHERE product_id=p.id AND status IN ('active','published') ORDER BY featured DESC,id ASC LIMIT 1) l ON TRUE LEFT JOIN LATERAL (SELECT image_url FROM product_images WHERE product_id=p.id ORDER BY sort_order ASC,id ASC LIMIT 1) pi ON TRUE WHERE {where_sql} ORDER BY p.id DESC LIMIT :limit OFFSET :offset"""), params).mappings().all()
        total = db.execute(text(f"SELECT COUNT(*) FROM products p WHERE {where_sql}"), params).scalar_one()
    return jsonify({"items": [_product_row(row) for row in rows], "page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)})


@commerce_bp.get("/products/<int:product_id>")
def product_detail(product_id):
    with SessionLocal() as db:
        row = db.execute(text("""SELECT p.id,p.name,p.slug,p.description,p.product_type,COALESCE(l.price,p.price) AS price,p.currency,p.sku,p.stock_quantity,pi.image_url,l.id AS listing_id,l.price AS listing_price FROM products p LEFT JOIN LATERAL (SELECT id,price FROM product_listings WHERE product_id=p.id AND status IN ('active','published') ORDER BY featured DESC,id ASC LIMIT 1) l ON TRUE LEFT JOIN LATERAL (SELECT image_url FROM product_images WHERE product_id=p.id ORDER BY sort_order ASC,id ASC LIMIT 1) pi ON TRUE WHERE p.id=:product_id AND p.status NOT IN ('draft','archived')"""), {"product_id": product_id}).mappings().first()
        if row is None:
            return jsonify({"error": "Product not found."}), 404
    return jsonify(_product_row(row))


@commerce_bp.get("/cart")
def get_cart():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        payload = _cart_payload(db, user_id)
        db.commit()
    return jsonify(payload)


@commerce_bp.post("/cart/items")
def add_cart_item():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    if not allow_cart_action(request.remote_addr, user_id):
        return jsonify({"error": "Too many cart requests. Please slow down and try again shortly."}), 429
    body = request.get_json(silent=True) or {}
    try:
        product_id = int(body.get("product_id"))
        quantity = int(body.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "product_id and quantity must be integers."}), 400
    if quantity < 1 or quantity > 100:
        return jsonify({"error": "Quantity must be between 1 and 100."}), 400
    with SessionLocal() as db:
        product = db.execute(text("SELECT id,product_type,stock_quantity,status FROM products WHERE id=:product_id AND status NOT IN ('draft','archived') FOR UPDATE"), {"product_id": product_id}).mappings().first()
        if product is None:
            return jsonify({"error": "Product not found."}), 404
        if product["product_type"] != "digital" and product["stock_quantity"] < quantity:
            return jsonify({"error": "Insufficient stock."}), 409
        cart_id = _get_or_create_cart(db, user_id)
        existing = db.execute(text("SELECT quantity FROM cart_items WHERE cart_id=:cart_id AND product_id=:product_id FOR UPDATE"), {"cart_id": cart_id, "product_id": product_id}).scalar_one_or_none()
        new_quantity = quantity if existing is None else existing + quantity
        if product["product_type"] != "digital" and new_quantity > product["stock_quantity"]:
            return jsonify({"error": "Requested quantity exceeds available stock."}), 409
        if existing is None:
            db.execute(text("INSERT INTO cart_items (cart_id,product_id,quantity,created_at) VALUES (:cart_id,:product_id,:quantity,NOW())"), {"cart_id": cart_id, "product_id": product_id, "quantity": new_quantity})
        else:
            db.execute(text("UPDATE cart_items SET quantity=:quantity WHERE cart_id=:cart_id AND product_id=:product_id"), {"quantity": new_quantity, "cart_id": cart_id, "product_id": product_id})
        db.execute(text("UPDATE carts SET updated_at=NOW() WHERE id=:cart_id"), {"cart_id": cart_id})
        payload = _cart_payload(db, user_id)
        db.commit()
    return jsonify(payload), 201


@commerce_bp.patch("/cart/items/<int:cart_item_id>")
def update_cart_item(cart_item_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    body = request.get_json(silent=True) or {}
    try:
        quantity = int(body.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be an integer."}), 400
    if quantity < 1 or quantity > 100:
        return jsonify({"error": "Quantity must be between 1 and 100."}), 400
    with SessionLocal() as db:
        row = db.execute(text("SELECT ci.id,p.stock_quantity,p.product_type FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id WHERE ci.id=:item_id AND c.user_id=:user_id FOR UPDATE"), {"item_id": cart_item_id, "user_id": user_id}).mappings().first()
        if row is None:
            return jsonify({"error": "Cart item not found."}), 404
        if row["product_type"] != "digital" and quantity > row["stock_quantity"]:
            return jsonify({"error": "Requested quantity exceeds available stock."}), 409
        db.execute(text("UPDATE cart_items SET quantity=:quantity WHERE id=:item_id"), {"quantity": quantity, "item_id": cart_item_id})
        db.execute(text("UPDATE carts SET updated_at=NOW() WHERE id=(SELECT cart_id FROM cart_items WHERE id=:item_id)"), {"item_id": cart_item_id})
        payload = _cart_payload(db, user_id)
        db.commit()
    return jsonify(payload)


@commerce_bp.delete("/cart/items/<int:cart_item_id>")
def delete_cart_item(cart_item_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        result = db.execute(text("DELETE FROM cart_items WHERE id=:item_id AND cart_id IN (SELECT id FROM carts WHERE user_id=:user_id)"), {"item_id": cart_item_id, "user_id": user_id})
        if result.rowcount == 0:
            return jsonify({"error": "Cart item not found."}), 404
        db.execute(text("UPDATE carts SET updated_at=NOW() WHERE user_id=:user_id"), {"user_id": user_id})
        payload = _cart_payload(db, user_id)
        db.commit()
    return jsonify(payload)


@commerce_bp.post("/checkout")
def create_checkout():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    if not allow_checkout(request.remote_addr, user_id):
        return jsonify({"error": "Too many checkout attempts. Please wait a few minutes and try again."}), 429
    with SessionLocal() as db:
        cart_id = db.execute(text("SELECT id FROM carts WHERE user_id=:user_id FOR UPDATE"), {"user_id": user_id}).scalar_one_or_none()
        if cart_id is None:
            return jsonify({"error": "Cart is empty."}), 400
        rows = db.execute(text("""SELECT ci.product_id,ci.quantity,p.name,p.product_type,p.stock_quantity,p.currency,l.id AS listing_id,COALESCE(l.price,p.price) AS unit_price FROM cart_items ci JOIN products p ON p.id=ci.product_id LEFT JOIN LATERAL (SELECT id,price FROM product_listings WHERE product_id=p.id AND status IN ('active','published') ORDER BY featured DESC,id ASC LIMIT 1) l ON TRUE WHERE ci.cart_id=:cart_id ORDER BY ci.id ASC FOR UPDATE OF ci,p"""), {"cart_id": cart_id}).mappings().all()
        if not rows:
            return jsonify({"error": "Cart is empty."}), 400
        currency = rows[0]["currency"] or "BDT"
        subtotal = Decimal("0")
        for row in rows:
            if row["product_type"] != "digital" and row["quantity"] > row["stock_quantity"]:
                return jsonify({"error": "Stock changed. Please review your cart.", "product_id": row["product_id"]}), 409
            subtotal += Decimal(str(row["unit_price"] or 0)) * row["quantity"]
        checkout_id = db.execute(text("INSERT INTO checkouts (user_id,status,currency,subtotal,shipping_amount,discount_amount,total_amount,created_at,updated_at) VALUES (:user_id,'pending',:currency,:subtotal,0,0,:total,NOW(),NOW()) RETURNING id"), {"user_id": user_id, "currency": currency, "subtotal": subtotal, "total": subtotal}).scalar_one()
        for row in rows:
            unit = Decimal(str(row["unit_price"] or 0))
            db.execute(text("INSERT INTO checkout_items (checkout_id,product_id,listing_id,quantity,unit_price,line_total) VALUES (:checkout_id,:product_id,:listing_id,:quantity,:unit_price,:line_total)"), {"checkout_id": checkout_id, "product_id": row["product_id"], "listing_id": row["listing_id"], "quantity": row["quantity"], "unit_price": unit, "line_total": unit * row["quantity"]})
        db.commit()
    return jsonify({"checkout_id": checkout_id, "status": "pending", "currency": currency, "subtotal": _money(subtotal), "shipping_amount": "0.00", "discount_amount": "0.00", "total_amount": _money(subtotal)}), 201


@commerce_bp.get("/checkout/<int:checkout_id>")
def get_checkout(checkout_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        checkout = db.execute(text("SELECT id,status,currency,subtotal,shipping_amount,discount_amount,total_amount,created_at,updated_at FROM checkouts WHERE id=:checkout_id AND user_id=:user_id"), {"checkout_id": checkout_id, "user_id": user_id}).mappings().first()
        if checkout is None:
            return jsonify({"error": "Checkout not found."}), 404
        items = db.execute(text("SELECT ci.id,ci.product_id,ci.listing_id,ci.quantity,ci.unit_price,ci.line_total,p.name,p.slug,p.product_type FROM checkout_items ci JOIN products p ON p.id=ci.product_id WHERE ci.checkout_id=:checkout_id ORDER BY ci.id ASC"), {"checkout_id": checkout_id}).mappings().all()
    return jsonify({"checkout_id": checkout["id"], "status": checkout["status"], "currency": checkout["currency"], "subtotal": _money(checkout["subtotal"]), "shipping_amount": _money(checkout["shipping_amount"]), "discount_amount": _money(checkout["discount_amount"]), "total_amount": _money(checkout["total_amount"]), "items": [{"id": i["id"], "product_id": i["product_id"], "listing_id": i["listing_id"], "name": i["name"], "slug": i["slug"], "product_type": i["product_type"], "quantity": i["quantity"], "unit_price": _money(i["unit_price"]), "line_total": _money(i["line_total"])} for i in items]})


def _order_number():
    return "NA-" + uuid4().hex[:20].upper()


@commerce_bp.post("/checkout/<int:checkout_id>/place-order")
def place_order(checkout_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    if not allow_checkout(request.remote_addr, user_id):
        return jsonify({"error": "Too many checkout attempts. Please wait a few minutes and try again."}), 429
    with SessionLocal() as db:
        checkout = db.execute(text("SELECT id,status,currency,subtotal,shipping_amount,discount_amount,total_amount,shipping_address_id FROM checkouts WHERE id=:checkout_id AND user_id=:user_id FOR UPDATE"), {"checkout_id": checkout_id, "user_id": user_id}).mappings().first()
        if checkout is None:
            return jsonify({"error": "Checkout not found."}), 404
        if checkout["status"] != "pending":
            return jsonify({"error": "Checkout is no longer available for ordering."}), 409
        items = db.execute(text("SELECT ci.product_id,ci.listing_id,ci.quantity,ci.unit_price,ci.line_total,p.name,p.product_type,p.stock_quantity,l.seller_id,l.supplier_product_id FROM checkout_items ci JOIN products p ON p.id=ci.product_id LEFT JOIN LATERAL (SELECT seller_id,supplier_product_id FROM product_listings WHERE id=ci.listing_id) l ON TRUE WHERE ci.checkout_id=:checkout_id ORDER BY ci.id ASC FOR UPDATE OF ci,p"""), {"checkout_id": checkout_id}).mappings().all()
        if not items:
            return jsonify({"error": "Checkout has no items."}), 400
        for item in items:
            if item["product_type"] != "digital" and item["supplier_product_id"] is None and item["quantity"] > item["stock_quantity"]:
                return jsonify({"error": "Insufficient stock while placing order.", "product_id": item["product_id"]}), 409
            if item["supplier_product_id"] is not None:
                supplier_stock = db.execute(text("SELECT supplier_stock,is_active FROM supplier_products WHERE id=:id FOR UPDATE"), {"id": item["supplier_product_id"]}).mappings().first()
                if not supplier_stock or not supplier_stock["is_active"] or supplier_stock["supplier_stock"] < item["quantity"]:
                    return jsonify({"error": "Supplier stock is unavailable.", "product_id": item["product_id"]}), 409
        order_number = _order_number()
        order_id = db.execute(text("INSERT INTO commerce_orders (order_number,user_id,shipping_address_id,status,payment_status,fulfillment_status,currency,subtotal,shipping_amount,discount_amount,total_amount,created_at,updated_at) VALUES (:order_number,:user_id,:shipping_address_id,'pending','pending','unfulfilled',:currency,:subtotal,:shipping_amount,:discount_amount,:total_amount,NOW(),NOW()) RETURNING id"), {"order_number": order_number, "user_id": user_id, "shipping_address_id": checkout["shipping_address_id"], "currency": checkout["currency"], "subtotal": checkout["subtotal"], "shipping_amount": checkout["shipping_amount"], "discount_amount": checkout["discount_amount"], "total_amount": checkout["total_amount"]}).scalar_one()
        for item in items:
            db.execute(text("INSERT INTO commerce_order_items (order_id,product_id,listing_id,seller_id,supplier_product_id,product_name,unit_price,quantity,line_total) VALUES (:order_id,:product_id,:listing_id,:seller_id,:supplier_product_id,:product_name,:unit_price,:quantity,:line_total)"), {"order_id": order_id, "product_id": item["product_id"], "listing_id": item["listing_id"], "seller_id": item["seller_id"], "supplier_product_id": item["supplier_product_id"], "product_name": item["name"], "unit_price": item["unit_price"], "quantity": item["quantity"], "line_total": item["line_total"]})
            if item["product_type"] != "digital" and item["supplier_product_id"] is None:
                db.execute(text("UPDATE products SET stock_quantity=stock_quantity-:quantity WHERE id=:product_id"), {"quantity": item["quantity"], "product_id": item["product_id"]})
        db.execute(text("UPDATE checkouts SET status='converted',updated_at=NOW() WHERE id=:checkout_id"), {"checkout_id": checkout_id})
        db.execute(text("DELETE FROM cart_items WHERE cart_id=(SELECT id FROM carts WHERE user_id=:user_id)"), {"user_id": user_id})
        db.execute(text("UPDATE carts SET updated_at=NOW() WHERE user_id=:user_id"), {"user_id": user_id})
        db.commit()
    return jsonify({"order_id": order_id, "order_number": order_number, "status": "pending", "payment_status": "pending", "fulfillment_status": "unfulfilled", "currency": checkout["currency"], "subtotal": _money(checkout["subtotal"]), "shipping_amount": _money(checkout["shipping_amount"]), "discount_amount": _money(checkout["discount_amount"]), "total_amount": _money(checkout["total_amount"])}), 201


@commerce_bp.get("/orders")
def list_orders():
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(50, max(1, int(request.args.get("per_page", "20"))))
    except ValueError:
        return jsonify({"error": "Invalid pagination."}), 400
    offset = (page - 1) * per_page
    with SessionLocal() as db:
        rows = db.execute(text("SELECT id,order_number,status,payment_status,fulfillment_status,currency,subtotal,shipping_amount,discount_amount,total_amount,created_at,updated_at FROM commerce_orders WHERE user_id=:user_id ORDER BY id DESC LIMIT :limit OFFSET :offset"), {"user_id": user_id, "limit": per_page, "offset": offset}).mappings().all()
        total = db.execute(text("SELECT COUNT(*) FROM commerce_orders WHERE user_id=:user_id"), {"user_id": user_id}).scalar_one()
    return jsonify({"items": [{"id": r["id"], "order_number": r["order_number"], "status": r["status"], "payment_status": r["payment_status"], "fulfillment_status": r["fulfillment_status"], "currency": r["currency"], "subtotal": _money(r["subtotal"]), "shipping_amount": _money(r["shipping_amount"]), "discount_amount": _money(r["discount_amount"]), "total_amount": _money(r["total_amount"]), "created_at": r["created_at"].isoformat() if r["created_at"] else None, "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None} for r in rows], "page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)})


@commerce_bp.get("/orders/<int:order_id>")
def order_detail(order_id):
    user_id = _user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401
    with SessionLocal() as db:
        order = db.execute(text("SELECT id,order_number,status,payment_status,fulfillment_status,currency,subtotal,shipping_amount,discount_amount,total_amount,created_at,updated_at FROM commerce_orders WHERE id=:order_id AND user_id=:user_id"), {"order_id": order_id, "user_id": user_id}).mappings().first()
        if order is None:
            return jsonify({"error": "Order not found."}), 404
        items = db.execute(text("SELECT product_id,listing_id,product_name,unit_price,quantity,line_total,seller_id,supplier_product_id FROM commerce_order_items WHERE order_id=:order_id ORDER BY id ASC"), {"order_id": order_id}).mappings().all()
    return jsonify({"id": order["id"], "order_number": order["order_number"], "status": order["status"], "payment_status": order["payment_status"], "fulfillment_status": order["fulfillment_status"], "currency": order["currency"], "subtotal": _money(order["subtotal"]), "shipping_amount": _money(order["shipping_amount"]), "discount_amount": _money(order["discount_amount"]), "total_amount": _money(order["total_amount"]), "created_at": order["created_at"].isoformat() if order["created_at"] else None, "updated_at": order["updated_at"].isoformat() if order["updated_at"] else None, "items": [{"product_id": i["product_id"], "listing_id": i["listing_id"], "product_name": i["product_name"], "unit_price": _money(i["unit_price"]), "quantity": i["quantity"], "line_total": _money(i["line_total"]), "seller_id": i["seller_id"], "supplier_product_id": i["supplier_product_id"]} for i in items]})


def register_commerce_routes(app):
    app.register_blueprint(commerce_bp)
