# Production database backups

The repository includes a GitHub Actions workflow at `.github/workflows/database-backup.yml`.

## Required setup

Create a GitHub Actions repository secret named `DATABASE_URL` containing the same PostgreSQL connection URL used by the Render service.

The workflow:

- runs daily at 02:17 UTC;
- can also be started manually from GitHub Actions;
- creates a PostgreSQL custom-format dump with `pg_dump`;
- writes a SHA-256 checksum next to the dump;
- stores the backup as a GitHub Actions artifact for 14 days.

## Migration safety

Never add destructive schema changes directly to the baseline migration `0001_initial_schema.py`.

For future schema changes:

1. create a new Alembic revision;
2. test it against a copy/staging database;
3. confirm a recent backup exists;
4. deploy the migration;
5. verify the application and database health.

The production start command remains:

```text
python scripts/migrate.py && gunicorn app:app
```

The backup workflow does not expose the database URL in logs; it is supplied through the GitHub Actions secret.
