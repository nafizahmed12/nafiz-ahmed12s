"""Replace generated SVG placeholder images with real photos from Wikimedia
Commons, for every published phone_catalog row.

Why Wikimedia Commons: every image on Commons carries an explicit free
license (CC-BY-SA, CC0, or public domain), so hotlinking it does not create
the copyright-infringement risk that hotlinking a manufacturer's or a
review site's copyrighted product photography would. This matters for
AdSense approval, which can be rejected for sites that host or embed
unlicensed copyrighted imagery.

This script only replaces images for phones that:
  - are status='published', AND
  - currently have no image_url, OR have the generated SVG placeholder
    (image_url starting with 'data:image/svg+xml;base64,') that migration
    0037_fix_phone_catalog_images.py installed as a fallback.

Phones that already have a real, working, non-placeholder image_url are
left untouched.

Not every phone will have a Wikimedia Commons photo -- niche or very
recent models often don't. Those rows are left on the existing SVG
placeholder and reported at the end so you know which models still need
a manually-sourced image.

Usage:
    # Preview only -- prints what WOULD change, writes nothing to the DB.
    python scripts/fetch_real_phone_images.py --dry-run

    # Apply the changes.
    python scripts/fetch_real_phone_images.py --apply

Requires the same DATABASE_URL environment variable the app itself uses
(the production Postgres URL when run against production).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "NafizStorePhoneImageLookup/1.0 (contact: store admin; one-off catalog image backfill)"
REQUEST_DELAY_SECONDS = 1.0  # be polite to Wikimedia's shared API


def _api_get(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{COMMONS_API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Commons filenames for these brands routinely drop the manufacturer name
# and use the product-line name instead -- e.g. Apple's own uploads are
# titled "Cosmic Orange iPhone 17 Pro Max.jpg", never "Apple iPhone ...".
# Listing the known product-line words explicitly (rather than guessing
# "the model's first word is probably a prefix") avoids the false
# positives/negatives that guessing produces on short model names like
# "OnePlus 13" or "vivo X200", where the first word is NOT a prefix to
# discard -- it's the only distinguishing part of the name.
# Not exhaustive: brands not listed here simply fall back to requiring the
# literal brand string, which is the safe default.
BRAND_ALIAS_WORDS = {
    "apple": {"iphone"},
    "samsung": {"galaxy"},
    "google": {"pixel"},
    "oneplus": {"one", "plus"},
}

# Variant/tier words that phone lineups reuse across sibling models (a
# "Pro", "Plus", "Ultra" etc. version of the same base name). A Commons
# file containing one of these that the searched-for model does NOT itself
# specify is almost certainly a *different*, more senior sibling -- e.g. a
# "14 Plus" or "14 Pro" file is not a match for a search for plain
# "iPhone 14". Checking for uninvited qualifier words catches this even
# when every token the model DOES specify (like a bare model number) is
# individually too generic to rule out on its own.
VARIANT_QUALIFIER_WORDS = {
    "pro", "plus", "ultra", "max", "mini", "air", "se", "note",
    "lite", "fe", "edge", "neo", "turbo", "gt",
}


def _normalized_words(value: str) -> set[str]:
    """Return whole alphanumeric tokens, avoiding substring false positives."""
    import re

    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _is_exact_commons_title_match(brand: str, model: str, title: str) -> bool:
    """Reject sibling variants and partial-token matches for phone photos."""
    brand_words = _normalized_words(brand)
    model_words = _normalized_words(model)
    title_words = _normalized_words(title)

    alias_words = BRAND_ALIAS_WORDS.get(brand.casefold(), set())
    brand_required = brand_words - alias_words
    brand_alias_hit = bool(title_words & alias_words)
    if not brand_required.issubset(title_words) and not brand_alias_hit:
        return False

    distinguishing = model_words - alias_words
    if not distinguishing or not distinguishing.issubset(title_words):
        return False

    # Do not use broad family/series photos as a model-specific product shot.
    if title_words & {"series", "family", "lineup", "comparison", "review"}:
        return False

    brand_compact = "".join(sorted(brand_words))
    title_compact = "".join(sorted(title_words))
    # Keep the compact-name allowance for split spellings such as One Plus.
    # Exact token matching above still governs the model identity.
    if brand_compact and not brand_required.issubset(title_words):
        if brand_compact not in title_compact and not brand_alias_hit:
            return False

    uninvited_qualifiers = {
        q for q in VARIANT_QUALIFIER_WORDS - model_words - alias_words
        if q not in brand_words
    }
    if title_words & uninvited_qualifiers:
        return False

    requested_qualifiers = distinguishing & VARIANT_QUALIFIER_WORDS
    if not requested_qualifiers.issubset(title_words):
        return False

    return True


def find_commons_image(brand: str, model: str) -> str | None:
    """Search Commons for a freely licensed photo matching the exact model.

    A candidate is accepted only when its filename contains every
    distinguishing model token as a whole word and no unrequested variant
    qualifier. Ambiguous family/series images are rejected.
    """
    query = f"{brand} {model} smartphone"
    try:
        search = _api_get({
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",
            "srlimit": "10",
        })
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    hits = search.get("query", {}).get("search", [])
    for hit in hits:
        title = hit.get("title", "")
        if not _is_exact_commons_title_match(brand, model, title):
            continue
        filename = title.split(":", 1)[-1]
        return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename)

    return None


def is_placeholder(image_url: str | None) -> bool:
    return not image_url or image_url.startswith("data:image/svg+xml;base64,")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview changes without writing to the database.")
    group.add_argument("--apply", action="store_true", help="Actually update image_url in the database.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N phones (for testing).")
    args = parser.parse_args()

    with SessionLocal() as db:
        rows = db.execute(text(
            "SELECT id, brand, model, image_url FROM phone_catalog "
            "WHERE status='published' ORDER BY brand, model"
        )).mappings().all()

    candidates = [r for r in rows if is_placeholder(r["image_url"])]
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"{len(rows)} published phones total; {len(candidates)} currently on a placeholder/missing image.\n")

    found: list[tuple[int, str, str, str]] = []
    not_found: list[tuple[str, str]] = []

    for row in candidates:
        url = find_commons_image(row["brand"], row["model"])
        time.sleep(REQUEST_DELAY_SECONDS)
        if url:
            found.append((row["id"], row["brand"], row["model"], url))
            print(f"  FOUND   {row['brand']} {row['model']} -> {url}")
        else:
            not_found.append((row["brand"], row["model"]))
            print(f"  --      {row['brand']} {row['model']} (no Commons match; left on placeholder)")

    print(f"\n{len(found)} matched, {len(not_found)} left unchanged.")

    if args.dry_run:
        print("\nDry run only -- no database changes were made. Re-run with --apply to write these updates.")
        return

    if not found:
        print("\nNothing to apply.")
        return

    with SessionLocal() as db:
        for phone_id, brand, model, url in found:
            db.execute(
                text("UPDATE phone_catalog SET image_url=:url WHERE id=:id"),
                {"url": url, "id": phone_id},
            )
        db.commit()
    print(f"\nApplied: updated image_url for {len(found)} phones.")

    if not_found:
        print(f"\n{len(not_found)} phones still have no real image (left on the generated placeholder):")
        for brand, model in not_found:
            print(f"  - {brand} {model}")


if __name__ == "__main__":
    main()
