from pathlib import Path


def test_admin_dashboard_exposes_manage_articles_shortcut():
    template = Path(__file__).resolve().parents[1] / "templates" / "admin.html"
    source = template.read_text(encoding="utf-8")

    assert 'href="{{ url_for(\'blog.admin_articles\') }}">Manage Articles</a>' in source
