# Sitemap & Indexing Checklist

## Current public sitemap
The application serves `/sitemap.xml` dynamically. Keep the clean public SEO URLs in the sitemap:

- `/`
- `/shop`
- `/about`
- `/contact`
- `/privacy-policy`
- `/terms`
- `/refund-policy`
- `/iphone-18`
- `/iphone-18-pro`
- `/iphone-18-pro-max`
- `/iphone-18-series`
- `/iphone-18-comparison`
- Valid public product detail URLs

## Indexing rules
1. Sitemap URLs must be absolute and canonical.
2. Do not add query-string variants to the sitemap.
3. Do not add `/static/*.html` legacy URLs when a clean URL exists.
4. Do not include private, account, checkout, API, or authentication endpoints.
5. Keep sitemap URLs aligned with pages that return successful, indexable responses.
6. Submit the production sitemap in Google Search Console after deployment.

## Google Search Console workflow
1. Open the property for `https://nafiz-ahmed12s.onrender.com`.
2. Go to **Sitemaps** and submit `sitemap.xml`.
3. Use **URL inspection** for the homepage and the five iPhone 18 SEO pages.
4. Request indexing for any newly deployed page that is not indexed.
5. Recheck **Pages / Indexing** for crawl, duplicate, canonical, and excluded-URL issues.

## Regression coverage
`tests/test_seo_indexing.py` verifies that the sitemap remains absolute and query-free, primary SEO landing pages remain discoverable, and robots.txt continues to reference the sitemap while blocking private routes.
