from publisher_admin_routes import normalize_seo_metadata


def test_seo_metadata_trims_values_and_uses_safe_defaults():
    result = normalize_seo_metadata({
        "seo_title": "  Best Android Phones  ",
        "canonical_url": " https://example.com/android-phones ",
        "og_title": "",
        "og_description": "  Social summary  ",
    }, "Article title", "Article excerpt")
    assert result == {
        "seo_title": "Best Android Phones",
        "canonical_url": "https://example.com/android-phones",
        "og_title": "Best Android Phones",
        "og_description": "Social summary",
    }


def test_seo_metadata_rejects_oversized_fields():
    try:
        normalize_seo_metadata({
            "seo_title": "x" * 201,
            "canonical_url": "",
            "og_title": "",
            "og_description": "",
        }, "Title", "Excerpt")
    except ValueError as exc:
        assert "SEO title" in str(exc)
    else:
        raise AssertionError("Oversized SEO title must be rejected")


def test_seo_metadata_rejects_non_http_canonical_url():
    try:
        normalize_seo_metadata({
            "seo_title": "",
            "canonical_url": "javascript:alert(1)",
            "og_title": "",
            "og_description": "",
        }, "Title", "Excerpt")
    except ValueError as exc:
        assert "Canonical URL" in str(exc)
    else:
        raise AssertionError("Unsafe canonical URL must be rejected")
