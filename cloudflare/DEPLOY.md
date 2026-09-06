# Cloudflare deployment (safe mode)

This repository is a Flask + SQLAlchemy + PostgreSQL application. The application already expects a normal Python runtime, Gunicorn, PostgreSQL, and Alembic migrations.

The safe Cloudflare setup is therefore:

`Your domain -> Cloudflare DNS/SSL -> Cloudflare Worker edge proxy -> Flask origin -> PostgreSQL`

This keeps the existing application and database unchanged. Do **not** point the Worker at a database or attempt to run the current `app.py` directly as a Python Worker until the database layer has been deliberately migrated and tested for the Workers/Pyodide runtime.

## 1. Deploy the existing Flask origin

Use the repository's existing production start command:

```text
python scripts/migrate.py && gunicorn app:app
```

The origin must provide HTTPS and must expose `/health`.

Required secrets/environment variables remain on the origin. Never commit them to Git.

## 2. Configure Cloudflare Worker

Install Wrangler and authenticate with the Cloudflare account that owns the domain.

From the repository root:

```bash
npx wrangler deploy cloudflare/worker.js --config cloudflare/wrangler.toml
```

Before deploying, set `ORIGIN_URL` to the real HTTPS origin URL. Do not guess this value.

For example:

```bash
npx wrangler secret put ORIGIN_URL --config cloudflare/wrangler.toml
```

If `ORIGIN_URL` is stored as a secret, remove the placeholder `[vars] ORIGIN_URL` value from the Wrangler configuration before deployment.

## 3. Attach the domain

After the Worker is deployed, add the desired custom domain to the Worker in the Cloudflare dashboard. Cloudflare then handles DNS, TLS, and the edge proxy.

## Why this approach is used

The existing application imports SQLAlchemy and `psycopg2-binary` during startup and has database access throughout multiple route modules. Cloudflare Python Workers execute under Pyodide/WebAssembly, and Python package support is limited to compatible pure/PyEmscripten packages. A direct Python Worker migration therefore needs a separate database compatibility project and should not be mixed into the first production deployment.

This branch intentionally leaves `main` and the production Flask code untouched.
