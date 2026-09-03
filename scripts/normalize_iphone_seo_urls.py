"""Normalize legacy iPhone 18 static URLs and register the Series Hub route."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "static/iphone-18-pro.html",
    ROOT / "static/iphone-18-pro-max.html",
    ROOT / "static/iphone-18-series.html",
)
REPLACEMENTS = {
    "/static/iphone-18-series.html": "/iphone-18-series",
    "/static/iphone-18-pro-max.html": "/iphone-18-pro-max",
    "/static/iphone-18-pro.html": "/iphone-18-pro",
    "/static/iphone-18.html": "/iphone-18",
}

for path in FILES:
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

security = ROOT / "admin_security.py"
text = security.read_text(encoding="utf-8")
route_marker = '    @app.route("/iphone-18-series")\n    def clean_iphone_18_series():\n        return app.send_static_file("iphone-18-series.html")\n\n'
if 'def clean_iphone_18_series()' not in text:
    text = text.replace('    @app.route("/iphone-18")\n', route_marker + '    @app.route("/iphone-18")\n', 1)

legacy_marker = '    @app.before_request\n    def handle_legacy_iphone_urls():'
if legacy_marker in text and '"/static/iphone-18-series.html": "/iphone-18-series"' not in text:
    text = text.replace(
        '        redirects = {\n',
        '        redirects = {\n            "/static/iphone-18-series.html": "/iphone-18-series",\n',
        1,
    )

old_condition = 'if request.path in {"/iphone-18", "/iphone-18-pro", "/iphone-18-pro-max"}'
new_condition = 'if request.path in {"/iphone-18-series", "/iphone-18", "/iphone-18-pro", "/iphone-18-pro-max"}'
text = text.replace(old_condition, new_condition, 1)

security.write_text(text, encoding="utf-8")
