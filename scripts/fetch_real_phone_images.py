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


def find_commons_image(brand: str, model: str) -> str | None:
    """Search Commons for a free-licensed photo matching brand+model.

    Returns a direct, stable image URL (via Special:FilePath, which always
    redirects to the current file regardless of internal filename changes)
    or None if nothing plausible was found.
    """
    query = f"{brand} {model} smartphone"
    try:
        search = _api_get({
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",  # File: namespace only
            "srlimit": "5",
        })
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    hits = search.get("query", {}).get("search", [])
    if not hits:
        return None

    brand_lower = brand.lower()
    brand_nospace = brand_lower.replace(" ", "")
    alias_words = BRAND_ALIAS_WORDS.get(brand_lower, set())
    # Every model word EXCEPT a known product-line alias is distinguishing.
    # This only ever removes a word when brand.lower() has a curated entry
    # for it, so it can't misfire on brands/models not in the map above.
    model_tokens = {t.lower() for t in model.split() if len(t) > 1}
    distinguishing_tokens = model_tokens - alias_words
    # Qualifier words the model itself asked for are fine to see in the
    # filename, and so is one that's actually embedded in the BRAND's own
    # name (e.g. "plus" inside "oneplus" -- a "One Plus 13" filename isn't
    # claiming a "13 Plus" sibling, that's just how the brand name is
    # spelled/split). Only a qualifier that belongs to neither flags a
    # genuinely different sibling model.
    uninvited_qualifiers = {
        q for q in (VARIANT_QUALIFIER_WORDS - model_tokens)
        if q not in brand_lower and q not in brand_nospace
    }

    for hit in hits:
        title = hit.get("title", "")  # e.g. "File:Samsung Galaxy S24 Ultra.jpg"
        title_lower = title.lower()
        title_nospace = title_lower.replace(" ", "")
        title_words = set(title_lower.replace(".", " ").replace("(", " ").replace(")", " ").split())
        # Compare with spaces stripped too, so brand names that Commons
        # uploaders sometimes split differently (e.g. "REDMAGIC" vs
        # "Red Magic", "OnePlus" vs "One Plus") still match.
        brand_hit = (
            brand_lower in title_lower
            or brand_nospace in title_nospace
            or any(word in title_lower for word in alias_words)
        )
        matched_distinguishing = {tok for tok in distinguishing_tokens if tok in title_lower}
        has_uninvited_qualifier = bool(title_words & uninvited_qualifiers)
        # Any qualifier word the model itself specifies (e.g. "pro" in
        # "13 Pro") must actually be present in the filename -- otherwise a
        # search for the Pro variant could match a base-model-only file
        # just because a plain token like the model number also matched.
        requested_qualifiers = distinguishing_tokens & VARIANT_QUALIFIER_WORDS
        missing_requested_qualifier = bool(requested_qualifiers - title_words)
        # Require: the brand (or its known alias, e.g. "iPhone" for Apple)
        # appears; at least one distinguishing model token appears (a
        # brand-only match, like a generic "Apple logo.png", isn't
        # enough); every qualifier word the model asked for is present;
        # and the file doesn't carry a variant word the model didn't ask
        # for (so an "iPhone 14" search rejects a "14 Plus" or "14 Pro"
        # file, even though "14" alone matches both).
        if (
            not brand_hit
            or not matched_distinguishing
            or has_uninvited_qualifier
            or missing_requested_qualifier
        ):
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
