# SEO Content Isolation Workflow

This project uses an isolated SEO workflow so new phones, products, categories, guides, or other topics do not accidentally replace existing SEO work.

## Non-negotiable rules

1. **One topic = one dedicated URL.** Do not reuse an existing SEO landing-page URL for a new topic.
2. **Never overwrite an existing SEO page just to target a new keyword.** Update an existing page only when the change genuinely improves that same topic.
3. **Every new page gets a unique slug, path, and canonical URL.** Register it in `seo/registry.json` in the same PR.
4. **One SEO task = one branch = one PR.** Branch from the latest `main` and keep unrelated work out of the branch.
5. **Merge first, start the next topic from updated `main`.** This prevents old branches from accidentally replacing newer work.
6. **Do not delete or rename an indexed SEO URL casually.** If a URL must change, plan the migration and redirect separately.
7. **Keep content claims verifiable.** Do not add unconfirmed product specifications, prices, release dates, or availability just to rank.
8. **Avoid keyword stuffing and duplicate doorway pages.** Each page should have a distinct search intent and useful content.
9. **Sitemap changes must be additive.** Adding a new page must not remove existing valid SEO URLs.
10. **Review the diff before merge.** A new-topic PR should normally add files/links rather than replace unrelated SEO pages.

## Standard workflow

```text
main
  │
  ├── seo/topic-a  → PR → merge
  │
  ├── seo/topic-b  → PR → merge
  │
  ├── seo/topic-c  → PR → merge
  │
  └── seo/topic-d  → PR → merge
```

Each topic is isolated. A later topic does not overwrite an earlier topic unless the PR explicitly changes the same file and that change is reviewed.

## Before creating a new SEO page

- Pick the exact search intent/topic.
- Choose a slug that does not already exist in `seo/registry.json`.
- Check that the canonical URL is unique.
- Create a new dedicated HTML page when the intent is genuinely different.
- Add internal links from relevant hub/category pages without removing existing links.
- Add the page to the registry.
- Run the registry validator.
- Review the PR diff for accidental deletions/replacements.

## Example

For a new phone, use a new URL such as:

```text
/static/iphone-17.html
```

Do **not** replace:

```text
/static/iphone-18.html
```

For a completely different topic, also use its own URL and registry entry.

## Important Git rule

Never build new work from an old feature branch after that branch has already been merged. Always create the next branch from current `main`. This keeps the history additive and makes accidental rollback/overwrite much less likely.
