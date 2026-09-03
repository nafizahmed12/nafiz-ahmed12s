"""Normalize legacy iPhone 18 static URLs in SEO HTML files.

This helper is intentionally additive: it only replaces the known public
legacy URLs and does not change page content or metadata beyond URL targets.
"""
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
