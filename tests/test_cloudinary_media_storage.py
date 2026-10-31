import sys
import types

import pytest


def test_cloudinary_storage_requires_a_configured_account(monkeypatch):
    from admin_editorial_routes import cloudinary_storage_configured

    for key in ("CLOUDINARY_URL", "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        monkeypatch.delenv(key, raising=False)
    assert cloudinary_storage_configured() is False

    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@example")
    assert cloudinary_storage_configured() is True


def test_cloudinary_upload_returns_only_a_secure_delivery_url(monkeypatch):
    from admin_editorial_routes import upload_image_to_cloudinary

    calls = {}

    def upload(file_obj, **kwargs):
        calls["kwargs"] = kwargs
        calls["bytes"] = file_obj.read()
        return {
            "public_id": "nafiztech/media/abc123",
            "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/nafiztech/media/abc123.png",
        }

    fake_cloudinary = types.ModuleType("cloudinary")
    fake_cloudinary.config = lambda: None
    fake_uploader = types.ModuleType("cloudinary.uploader")
    fake_uploader.upload = upload
    fake_cloudinary.uploader = fake_uploader
    monkeypatch.setitem(sys.modules, "cloudinary", fake_cloudinary)
    monkeypatch.setitem(sys.modules, "cloudinary.uploader", fake_uploader)
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@example")

    result = upload_image_to_cloudinary(b"image-bytes", "abc123.png")

    assert result == {
        "public_id": "nafiztech/media/abc123",
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/nafiztech/media/abc123.png",
    }
    assert calls["bytes"] == b"image-bytes"
    assert calls["kwargs"]["resource_type"] == "image"
    assert calls["kwargs"]["folder"] == "nafiztech/media"


def test_cloudinary_upload_rejects_non_https_delivery_urls(monkeypatch):
    from admin_editorial_routes import upload_image_to_cloudinary

    fake_cloudinary = types.ModuleType("cloudinary")
    fake_cloudinary.config = lambda: None
    fake_uploader = types.ModuleType("cloudinary.uploader")
    fake_uploader.upload = lambda *_args, **_kwargs: {
        "public_id": "nafiztech/media/abc123",
        "secure_url": "http://example.com/image.png",
    }
    fake_cloudinary.uploader = fake_uploader
    monkeypatch.setitem(sys.modules, "cloudinary", fake_cloudinary)
    monkeypatch.setitem(sys.modules, "cloudinary.uploader", fake_uploader)
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@example")

    with pytest.raises(RuntimeError, match="secure HTTPS URL"):
        upload_image_to_cloudinary(b"image-bytes", "abc123.png")


def test_cloudinary_delete_uses_the_stored_public_id(monkeypatch):
    from admin_editorial_routes import delete_cloudinary_image

    calls = {}
    fake_cloudinary = types.ModuleType("cloudinary")
    fake_cloudinary.config = lambda: None
    fake_uploader = types.ModuleType("cloudinary.uploader")

    def destroy(public_id, **kwargs):
        calls["public_id"] = public_id
        calls["kwargs"] = kwargs
        return {"result": "ok"}

    fake_uploader.destroy = destroy
    fake_cloudinary.uploader = fake_uploader
    monkeypatch.setitem(sys.modules, "cloudinary", fake_cloudinary)
    monkeypatch.setitem(sys.modules, "cloudinary.uploader", fake_uploader)
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@example")

    delete_cloudinary_image("nafiztech/media/abc123")

    assert calls["public_id"] == "nafiztech/media/abc123"
    assert calls["kwargs"]["resource_type"] == "image"
