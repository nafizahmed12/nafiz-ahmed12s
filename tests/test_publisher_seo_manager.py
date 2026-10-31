from publisher_admin_routes import audit_article_seo


def test_seo_audit_flags_missing_metadata():
    result = audit_article_seo({
        "seo_description": "",
        "excerpt": "",
        "featured_image_url": "",
    })
    assert result == ["Missing SEO description", "Missing excerpt", "Missing featured image"]


def test_seo_audit_flags_description_outside_recommended_length():
    result = audit_article_seo({
        "seo_description": "Short description",
        "excerpt": "A useful summary",
        "featured_image_url": "https://example.com/image.jpg",
    })
    assert result == ["SEO description too short"]


def test_seo_audit_accepts_complete_metadata():
    result = audit_article_seo({
        "seo_description": "A practical guide to choosing a smartphone with strong battery life, a clear display, reliable performance and useful camera features.",
        "excerpt": "A practical smartphone buying guide.",
        "featured_image_url": "https://example.com/image.jpg",
    })
    assert result == []
