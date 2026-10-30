import hmac
import os
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal

article_publish_bp = Blueprint("article_publish_api", __name__)


def _validated_article(payload):
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required.")

    title = str(payload.get("title") or "").strip()
    slug = str(payload.get("slug") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    excerpt = str(payload.get("excerpt") or "").strip()
    content = str(payload.get("content") or "").strip()
    category = str(payload.get("category") or "Technology").strip() or "Technology"
    image = str(payload.get("featured_image_url") or "").strip()
    seo_description = str(payload.get("seo_description") or excerpt).strip()
    status = str(payload.get("status") or "draft").strip().lower()

    if not title or len(title) > 200:
        raise ValueError("Title is required and must be 200 characters or fewer.")
    if not slug or len(slug) > 220 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("A valid lowercase article slug is required.")
    if len(excerpt) > 320 or len(seo_description) > 320:
        raise ValueError("Excerpt and SEO description must be 320 characters or fewer.")
    if len(content) < 80:
        raise ValueError("Article content must contain at least 80 characters.")
    if len(category) > 80 or len(image) > 2048:
        raise ValueError("Category or featured image URL is too long.")
    if status not in {"draft", "published"}:
        raise ValueError("Status must be draft or published.")

    return {
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "content": content,
        "category": category,
        "image": image,
        "seo_description": seo_description,
        "status": status,
    }


@article_publish_bp.post("/api/articles")
def publish_article():
    configured_token = os.getenv("ARTICLE_PUBLISH_API_TOKEN", "").strip()
    supplied_header = request.headers.get("Authorization", "")
    supplied_token = supplied_header[7:].strip() if supplied_header.startswith("Bearer ") else ""

    if not configured_token:
        return jsonify({"error": "Article publishing API is not configured."}), 503
    if not supplied_token or not hmac.compare_digest(supplied_token, configured_token):
        return jsonify({"error": "Unauthorized"}), 401

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    try:
        article = _validated_article(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    now = datetime.now(timezone.utc)
    published_at = now if article["status"] == "published" else None
    params = {
        **article,
        "now": now,
        "published_at": published_at,
    }

    try:
        with SessionLocal() as db:
            result = db.execute(
                text("""INSERT INTO blog_articles
                    (title,slug,excerpt,content,category,featured_image_url,seo_description,status,created_at,updated_at,published_at)
                    VALUES (:title,:slug,:excerpt,:content,:category,:image,:seo_description,:status,:now,:now,:published_at)
                    RETURNING id"""),
                params,
            )
            article_id = result.scalar_one()
            db.commit()
    except IntegrityError:
        return jsonify({"error": "An article with this slug already exists."}), 409

    return jsonify({
        "id": article_id,
        "slug": article["slug"],
        "status": article["status"],
        "published_at": published_at.isoformat() if published_at else None,
    }), 201


def register_article_publish_api(app):
    if "article_publish_api" not in app.blueprints:
        app.register_blueprint(article_publish_bp)
