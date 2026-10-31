import io
from datetime import datetime, timezone

import pytest


def test_editorial_tools_routes_are_registered_and_owner_only():
    from wsgi import app

    paths = {rule.rule for rule in app.url_map.iter_rules()}
    expected = {
        "/admin/media",
        "/admin/media/upload",
        "/admin/schedule",
        "/admin/articles/<int:article_id>/history",
        "/admin/activity",
        "/admin/settings",
    }
    assert expected.issubset(paths)
    for path in ("/admin/media", "/admin/schedule", "/admin/activity", "/admin/settings"):
        response = app.test_client().get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_schedule_datetime_rejects_past_and_invalid_values():
    from admin_editorial_routes import normalize_schedule_datetime

    with pytest.raises(ValueError):
        normalize_schedule_datetime("not-a-date", now=datetime(2026, 10, 31, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        normalize_schedule_datetime("2020-01-01T10:00", now=datetime(2026, 10, 31, tzinfo=timezone.utc))


def test_site_settings_allow_only_known_public_fields():
    from admin_editorial_routes import normalize_site_settings

    clean = normalize_site_settings({
        "site_title": "  NafizTech  ",
        "site_tagline": "Technology, clearly explained",
        "site_description": "Independent technology publishing.",
        "admin_password": "must-not-be-saved",
        "SECRET_KEY": "must-not-be-saved",
    })
    assert clean == {
        "site_title": "NafizTech",
        "site_tagline": "Technology, clearly explained",
        "site_description": "Independent technology publishing.",
    }


def test_media_upload_checks_image_signature_and_extension():
    from admin_editorial_routes import validate_media_upload

    png = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"
    result = validate_media_upload("cover.png", "image/png", png)
    assert result["extension"] == ".png"
    assert result["mime_type"] == "image/png"
    with pytest.raises(ValueError):
        validate_media_upload("cover.png", "image/png", b"not-a-png")
    with pytest.raises(ValueError):
        validate_media_upload("cover.exe", "application/octet-stream", b"MZbad")


def test_revision_snapshot_is_json_serializable_and_excludes_unneeded_fields():
    from admin_editorial_routes import build_article_snapshot

    snapshot = build_article_snapshot({
        "id": 12, "title": "Example", "slug": "example", "content": "Article body",
        "status": "draft", "published_at": None, "created_at": None,
    })
    assert snapshot["id"] == 12
    assert snapshot["title"] == "Example"
    assert "password" not in snapshot



def test_due_scheduled_articles_are_published():
    import uuid
    from sqlalchemy import text
    from database import SessionLocal
    from admin_editorial_routes import publish_due_articles

    slug = "scheduled-ci-" + uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        article_id = db.execute(text("""INSERT INTO blog_articles
            (title,slug,excerpt,content,category,featured_image_url,seo_description,status,created_at,updated_at,published_at,scheduled_at)
            VALUES ('Scheduled CI article',:slug,'','This is a test article body with enough content to satisfy the publishing schema.',
            'Technology',NULL,'','scheduled',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,NULL,'2020-01-01 00:00:00+00')
            RETURNING id"""), {"slug": slug}).scalar_one()
        db.commit()
        count = publish_due_articles(db)
        row = db.execute(text("SELECT status,published_at,scheduled_at FROM blog_articles WHERE id=:id"), {"id": article_id}).mappings().one()
        assert count >= 1
        assert row["status"] == "published"
        assert row["published_at"] is not None
        assert row["scheduled_at"] is None
        db.execute(text("DELETE FROM blog_articles WHERE id=:id"), {"id": article_id})
        db.commit()


def test_editorial_api_schedule_runner_requires_a_bearer_token(monkeypatch):
    from wsgi import app

    monkeypatch.setenv("SCHEDULED_PUBLISH_TOKEN", "test-cron-secret")
    response = app.test_client().post("/api/internal/publish-scheduled")
    assert response.status_code == 401
