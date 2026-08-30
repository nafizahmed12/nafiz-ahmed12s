from flask import Blueprint, jsonify, request

from sqlalchemy import text

from database import SessionLocal
from admin_auth import admin_required

admin_reviews_bp = Blueprint("admin_reviews", __name__)

REVIEW_STATUSES = {"pending", "approved", "rejected"}


@admin_reviews_bp.get("/api/admin/reviews")
@admin_required
def admin_reviews_api():
    status = request.args.get("status", "pending").strip().lower()
    if status not in REVIEW_STATUSES:
        return jsonify({"error": "Invalid status filter."}), 400
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT r.id,r.product_id,r.rating,r.title,r.body,r.status,r.created_at,
                   p.name AS product_name, u.username, u.email
            FROM product_reviews r
            JOIN products p ON p.id=r.product_id
            JOIN users u ON u.id=r.user_id
            WHERE r.status=:status
            ORDER BY r.created_at ASC
            LIMIT 200
        """), {"status": status}).mappings().all()
    return jsonify({"items": [
        {
            "id": r["id"], "product_id": r["product_id"], "product_name": r["product_name"],
            "rating": r["rating"], "title": r["title"] or "", "body": r["body"],
            "username": r["username"], "email": r["email"], "status": r["status"],
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else (str(r["created_at"]) if r["created_at"] else None),
        } for r in rows
    ]})


@admin_reviews_bp.patch("/api/admin/reviews/<int:review_id>")
@admin_required
def update_admin_review(review_id):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    if status not in ("approved", "rejected"):
        return jsonify({"error": "status must be 'approved' or 'rejected'."}), 400
    with SessionLocal() as db:
        exists = db.execute(text("SELECT id FROM product_reviews WHERE id=:id"), {"id": review_id}).scalar_one_or_none()
        if exists is None:
            return jsonify({"error": "Review not found."}), 404
        db.execute(text("UPDATE product_reviews SET status=:status,updated_at=NOW() WHERE id=:id"), {"id": review_id, "status": status})
        db.commit()
    return jsonify({"success": True, "review_id": review_id, "status": status})


def register_admin_review_routes(app):
    if "admin_reviews" not in app.blueprints:
        app.register_blueprint(admin_reviews_bp)
