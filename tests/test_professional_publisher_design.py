from pathlib import Path

from app import app


TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def test_homepage_renders_professional_publisher_identity():
    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Understand the tech." in body
    assert "The latest from NafizTech" in body
    assert "Independent technology publication" in body
    homepage_template = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    assert "Nafiz Store" not in homepage_template


def test_article_templates_use_consistent_nafiztech_branding_and_clean_canonicals():
    listing = (TEMPLATES / "blog_index.html").read_text(encoding="utf-8")
    article = (TEMPLATES / "blog_article.html").read_text(encoding="utf-8")

    for template in (listing, article):
        assert "NafizTech" in template
        assert "url_for('blog.blog_index', _external=True)" in template or "url_for('blog.blog_article', slug=article.slug, _external=True)" in template
        assert "Nafiz Store" not in template
        assert "prefers-reduced-motion:reduce" in template


def test_homepage_and_article_pages_include_responsive_layout_rules():
    homepage = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    listing = (TEMPLATES / "blog_index.html").read_text(encoding="utf-8")
    article = (TEMPLATES / "blog_article.html").read_text(encoding="utf-8")

    for template in (homepage, listing, article):
        assert "@media(max-width:" in template
        assert "a:focus-visible" in template


def test_homepage_uses_real_official_product_photography():
    homepage = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert 'class="hero-product-photo"' in homepage
    assert "store.storeimages.cdn-apple.com" in homepage
    assert "official Apple product photo" in homepage
    assert "Abstract technology illustration" not in homepage
