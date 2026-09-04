# Sitemap XML standard

The dynamic `/sitemap.xml` response is generated from `admin_security.py` so the production response uses one canonical XML format.

Requirements:
- XML declaration with UTF-8 encoding.
- Sitemap protocol namespace: `http://www.sitemaps.org/schemas/sitemap/0.9`.
- One normalized absolute URL per `<loc>` with no query string.
- `<lastmod>` is included only where a real recent content update date is known; dates use `YYYY-MM-DD`.
- No `/static/` SEO landing-page URLs.
