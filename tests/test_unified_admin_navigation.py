from pathlib import Path


PUBLISHER_NAV = [
    ("/admin", "Dashboard"),
    ("/admin/publisher", "Publisher Dashboard"),
    ("/admin/articles", "Article Manager"),
    ("/admin/phones", "Phone Catalog"),
    ("/admin/seo", "SEO Manager"),
    ("/admin/bulk", "Bulk Editor"),
]


def test_admin_dashboard_links_to_all_publisher_tools():
    template = Path("templates/admin.html").read_text(encoding="utf-8")
    for href, label in PUBLISHER_NAV[1:]:
        assert href in template
        assert label in template


def test_publisher_pages_share_unified_navigation():
    templates = [
        "templates/admin_publisher_dashboard.html",
        "templates/admin_publisher_seo.html",
        "templates/admin_publisher_bulk.html",
        "templates/admin_articles.html",
        "templates/admin_phones.html",
    ]
    for filename in templates:
        content = Path(filename).read_text(encoding="utf-8")
        assert "{% include 'admin_unified_nav.html' %}" in content, filename

    partial = Path("templates/admin_unified_nav.html").read_text(encoding="utf-8")
    assert 'class="admin-unified-nav"' in partial


def test_unified_navigation_is_mobile_responsive():
    partial = Path("templates/admin_unified_nav.html").read_text(encoding="utf-8")
    assert "aria-label" in partial
    for href, _ in PUBLISHER_NAV:
        assert href in partial, href
    assert "@media" in partial
    assert "overflow-x:auto" in partial
