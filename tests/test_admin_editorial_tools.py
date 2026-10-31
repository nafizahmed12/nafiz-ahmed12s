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
