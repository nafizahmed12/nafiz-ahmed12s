#!/usr/bin/env python3
"""Validate SEO registry uniqueness and isolation rules."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "seo" / "registry.json"


def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    required = ("topic", "slug", "path", "canonical")

    if not pages:
        raise SystemExit("SEO registry must contain at least one page")

    for index, page in enumerate(pages, start=1):
        missing = [key for key in required if not page.get(key)]
        if missing:
            raise SystemExit(f"SEO registry entry {index} missing: {', '.join(missing)}")

    for key in ("slug", "path", "canonical"):
        values = [page[key].strip().lower() for page in pages]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise SystemExit(f"Duplicate SEO {key}: {', '.join(duplicates)}")

    slugs = {page["slug"].strip().lower() for page in pages}
    paths = {page["path"].strip().lower() for page in pages}
    for page in pages:
        expected = f"/static/{page['slug'].strip()}.html".lower()
        if page["path"].strip().lower() != expected:
            raise SystemExit(
                f"SEO path/slug mismatch for {page['topic']}: "
                f"expected {expected}, got {page['path']}"
            )
        if page["slug"].strip().lower() not in slugs or page["path"].strip().lower() not in paths:
            raise SystemExit(f"Invalid SEO registry entry: {page['topic']}")

    print(f"SEO registry OK: {len(pages)} unique pages")


if __name__ == "__main__":
    main()
