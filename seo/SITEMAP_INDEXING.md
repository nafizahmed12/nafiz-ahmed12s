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
6. Public SEO pages must use `index,follow` and a canonical URL pointing to the clean public URL.
7. Keep `robots.txt` free of any `Disallow: /` rule; private paths only should be blocked.
8. Submit the production sitemap in Google Search Console after deployment.

## AdSense readiness
- Keep original, useful product/guide content visible on public pages.
- Keep About, Contact, Privacy, Terms and Refund/Return navigation easy to find.
- Disclose affiliate relationships clearly near relevant recommendations.
- Do not publish misleading prices, specifications, stock claims, reviews or ratings.
- Keep private/account/checkout pages out of crawlable SEO surfaces.

## Google Search Console workflow
1. Open the property for `https://nafiz-ahmed12s.onrender.com`.
2. Go to **Sitemaps** and submit `sitemap.xml`.
3. Use **URL inspection** for the homepage and the five iPhone 18 SEO pages.
4. After each robots/sitemap deployment, re-run URL Inspection so Google can fetch the current robots rules rather than relying on an older crawl result.
5. Request indexing for any newly deployed page that is not indexed.
6. Recheck **Pages / Indexing** for crawl, duplicate, canonical, and excluded-URL issues.

## Regression coverage
`tests/test_seo_indexing.py` verifies valid query-free sitemap URLs, primary SEO landing-page discovery, successful indexable HTML with self-canonicals, hub-to-model internal links, and robots.txt behavior that allows public SEO pages while blocking private routes.
