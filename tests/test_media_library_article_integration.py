import html

from markupsafe import Markup


def test_article_content_renders_library_markdown_images():
    from blog_routes import render_article_content

    rendered = str(render_article_content(
        "First paragraph.\n\n![Phone cover](https://example.com/phone.webp)\n\nLast paragraph."
    ))

    assert "First paragraph." in rendered
    assert '<img src="https://example.com/phone.webp" alt="Phone cover"' in rendered
    assert "loading=\"lazy\"" in rendered
    assert "Last paragraph." in rendered


def test_article_content_escapes_html_and_rejects_unsafe_image_urls():
    from blog_routes import render_article_content

    rendered = str(render_article_content(
        '<script>alert("x")</script>\n![Bad](javascript:alert(1))'
    ))

    assert html.escape('<script>alert("x")</script>') in rendered
    assert "<script>" not in rendered
    assert "javascript:" not in rendered
    assert "<img " not in rendered


def test_article_content_accepts_internal_media_library_urls():
    from blog_routes import render_article_content

    rendered = str(render_article_content(
        "![Editorial photo](/media/0123456789abcdef0123456789abcdef.webp)"
    ))

    assert 'src="/media/0123456789abcdef0123456789abcdef.webp"' in rendered
