from datetime import datetime, timezone
import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from admin_auth import admin_required

blog_bp = Blueprint("blog", __name__)


def _slugify(value):
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", (value or "").strip().lower())
    value = re.sub(r"[\s-]+", "-", value).strip("-")
    return value[:220]


def _validate_form():
    title = request.form.get("title", "").strip()
    slug = _slugify(request.form.get("slug", "")) or _slugify(title)
    excerpt = request.form.get("excerpt", "").strip()
    content = request.form.get("content", "").strip()
    category = request.form.get("category", "Technology").strip() or "Technology"
    image = request.form.get("featured_image_url", "").strip()
    seo_description = request.form.get("seo_description", "").strip() or excerpt
    status = request.form.get("status", "draft").strip().lower()
    if not title or len(title) > 200:
        raise ValueError("Title is required and must be 200 characters or fewer.")
    if not slug or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Slug may contain only lowercase letters, numbers and hyphens.")
    if len(excerpt) > 320 or len(seo_description) > 320:
        raise ValueError("Excerpt and SEO description must be 320 characters or fewer.")
    if len(content) < 80:
        raise ValueError("Article content should contain at least 80 characters.")
    if len(category) > 80 or len(image) > 2048:
        raise ValueError("Category or image URL is too long.")
    if status not in {"draft", "published"}:
        raise ValueError("Status must be draft or published.")
    return title, slug, excerpt, content, category, image, seo_description, status


@blog_bp.get("/blog")
def blog_index():
    with SessionLocal() as db:
        articles = db.execute(text("""SELECT id,title,slug,excerpt,category,featured_image_url,published_at
            FROM blog_articles WHERE status='published' AND published_at IS NOT NULL
            ORDER BY published_at DESC, id DESC LIMIT 100""")).mappings().all()
    return render_template("blog_index.html", articles=articles)


@blog_bp.get("/blog/<slug>")
def blog_article(slug):
    with SessionLocal() as db:
        article = db.execute(text("""SELECT id,title,slug,excerpt,content,category,featured_image_url,seo_description,published_at,updated_at
            FROM blog_articles WHERE slug=:slug AND status='published' AND published_at IS NOT NULL"""), {"slug": slug}).mappings().first()
        if article is None:
            abort(404)
        related = db.execute(text("""SELECT id,title,slug,excerpt,category,featured_image_url,published_at
            FROM blog_articles
            WHERE status='published' AND published_at IS NOT NULL
              AND id <> :id AND category = :category
            ORDER BY published_at DESC, id DESC LIMIT 3"""),
            {"id": article["id"], "category": article["category"]}).mappings().all()
        if len(related) < 3:
            related = db.execute(text("""SELECT id,title,slug,excerpt,category,featured_image_url,published_at
                FROM blog_articles
                WHERE status='published' AND published_at IS NOT NULL AND id <> :id
                ORDER BY published_at DESC, id DESC LIMIT 3"""),
                {"id": article["id"]}).mappings().all()
    return render_template("blog_article.html", article=article, related=related)


@blog_bp.get("/admin/articles")
@admin_required
def admin_articles():
    with SessionLocal() as db:
        articles = db.execute(text("""SELECT id,title,slug,excerpt,category,status,featured_image_url,created_at,updated_at,published_at
            FROM blog_articles ORDER BY id DESC""")).mappings().all()
    return render_template("admin_articles.html", articles=articles, article=None)


@blog_bp.post("/admin/articles")
@admin_required
def create_article():
    try:
        title, slug, excerpt, content, category, image, seo_description, status = _validate_form()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("blog.admin_articles"))
    now = datetime.now(timezone.utc)
    published_at = now if status == "published" else None
    with SessionLocal() as db:
        try:
            db.execute(text("""INSERT INTO blog_articles
                (title,slug,excerpt,content,category,featured_image_url,seo_description,status,created_at,updated_at,published_at)
                VALUES (:title,:slug,:excerpt,:content,:category,:image,:seo_description,:status,:now,:now,:published_at)"""), locals())
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("An article with this slug already exists.", "error")
            return redirect(url_for("blog.admin_articles"))
    flash("Article created successfully.", "success")
    return redirect(url_for("blog.admin_articles"))


@blog_bp.get("/admin/articles/<int:article_id>/edit")
@admin_required
def edit_article(article_id):
    with SessionLocal() as db:
        article = db.execute(text("SELECT * FROM blog_articles WHERE id=:id"), {"id": article_id}).mappings().first()
    if article is None:
        abort(404)
    with SessionLocal() as db:
        articles = db.execute(text("""SELECT id,title,slug,excerpt,category,status,featured_image_url,created_at,updated_at,published_at
            FROM blog_articles ORDER BY id DESC""")).mappings().all()
    return render_template("admin_articles.html", articles=articles, article=article)


@blog_bp.post("/admin/articles/<int:article_id>/edit")
@admin_required
def update_article(article_id):
    try:
        title, slug, excerpt, content, category, image, seo_description, status = _validate_form()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("blog.edit_article", article_id=article_id))
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        existing = db.execute(text("SELECT status,published_at FROM blog_articles WHERE id=:id"), {"id": article_id}).mappings().first()
        if existing is None:
            abort(404)
        published_at = existing["published_at"]
        if status == "published" and published_at is None:
            published_at = now
        if status == "draft":
            published_at = None
        try:
            db.execute(text("""UPDATE blog_articles SET title=:title,slug=:slug,excerpt=:excerpt,content=:content,
                category=:category,featured_image_url=:image,seo_description=:seo_description,status=:status,
                updated_at=:now,published_at=:published_at WHERE id=:id"""), locals())
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("An article with this slug already exists.", "error")
            return redirect(url_for("blog.edit_article", article_id=article_id))
    flash("Article updated successfully.", "success")
    return redirect(url_for("blog.admin_articles"))


@blog_bp.post("/admin/articles/<int:article_id>/delete")
@admin_required
def delete_article(article_id):
    with SessionLocal() as db:
        result = db.execute(text("DELETE FROM blog_articles WHERE id=:id"), {"id": article_id})
        if result.rowcount == 0:
            db.rollback()
            abort(404)
        db.commit()
    flash("Article deleted.", "success")
    return redirect(url_for("blog.admin_articles"))


def register_blog_routes(app):
    if "blog" not in app.blueprints:
        app.register_blueprint(blog_bp)
