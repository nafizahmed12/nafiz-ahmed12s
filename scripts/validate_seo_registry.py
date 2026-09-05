#!/usr/bin/env python3
"""Validate SEO registry uniqueness and isolation rules, and check that the
registry stays in sync with the live sitemap (no drift between what the
registry claims exists and what is actually published)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "seo" / "registry.json"
SITEMAP = ROOT / "static" / "sitemap.xml"


def check_sitemap_drift(pages: list[dict]) -> None:
    """Every /static/<slug>.html-style URL present in sitemap.xml must have a
    matching registry entry, and vice versa. Catches routes (like a page added
    straight to app.py + sitemap) that were never registered."""
    if not SITEMAP.exists():
        print(f"Skipping sitemap drift check: {SITEMAP} not found")
        return

    sitemap_text = SITEMAP.read_text(encoding="utf-8")
    sitemap_locs = re.findall(r"<loc>(.*?)</loc>", sitemap_text)

    # Only compare against registry-managed static content pages; sitemap
    # entries for the homepage, /shop, /about, legal pages, etc. are not
    # registry-tracked topics and are intentionally out of scope here.
    registry_slugs = {page["slug"].strip().lower() for page in pages}
    registry_canonicals = {page["canonical"].strip().lower() for page in pages}

    # A sitemap URL is "registry-relevant" if it matches the canonical URL
    # pattern used by registry pages (same host, single path segment that
    # looks like a content slug rather than a known non-registry route).
    known_non_registry_paths = {
        "", "shop", "about", "contact", "privacy-policy", "terms", "refund-policy",
    }

    for loc in sitemap_locs:
        loc_clean = loc.strip().lower()
        if loc_clean in registry_canonicals:
            continue
        # Derive the path (not the host) so "https://host/" -> "" (homepage),
        # "https://host/shop" -> "shop", etc. Using the full URL's rsplit
        # previously matched on the hostname for the homepage case.
        path_only = re.sub(r"^https?://[^/]+/?", "", loc_clean).rstrip("/")
        if path_only in known_non_registry_paths:
            continue
        raise SystemExit(
            f"Sitemap URL not found in SEO registry (drift detected): {loc}\n"
            f"  -> Either add a registry entry for slug '{path_only}', or "
            f"remove it from static/sitemap.xml if it should not be tracked."
        )

    for slug in registry_slugs:
        if not any(slug in loc.lower() for loc in sitemap_locs):
            raise SystemExit(
                f"Registry slug '{slug}' has no matching URL in static/sitemap.xml "
                f"(registry claims a page that isn't published)."
            )


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

    check_sitemap_drift(pages)

    print(f"SEO registry OK: {len(pages)} unique pages, no sitemap drift")


if __name__ == "__main__":
    main()
