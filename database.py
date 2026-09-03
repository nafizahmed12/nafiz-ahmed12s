import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url():
    """Return the configured database URL."""
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = "postgresql+psycopg2://" + database_url[len("postgres://"):]
        elif database_url.startswith("postgresql://"):
            database_url = "postgresql+psycopg2://" + database_url[len("postgresql://"):]
        return database_url

    if os.getenv("USE_SQLITE", "").strip() == "1":
        return "sqlite:///messages.db"

    raise RuntimeError(
        "DATABASE_URL is not configured. Add the Render PostgreSQL "
        "DATABASE_URL environment variable, or set USE_SQLITE=1 for local development."
    )


def create_database_engine():
    url = get_database_url()

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10"))}

    engine_options = {"connect_args": connect_args, "pool_pre_ping": True}

    if not url.startswith("sqlite"):
        engine_options.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
                "pool_use_lifo": True,
            }
        )

    return create_engine(url, **engine_options)


engine = create_database_engine()


@event.listens_for(engine, "connect")
def _register_sqlite_compatibility_functions(dbapi_connection, connection_record):
    """Provide PostgreSQL-compatible NOW() for local SQLite development/tests."""
    if engine.dialect.name == "sqlite":
        dbapi_connection.create_function(
            "NOW", 0, lambda: datetime.now(timezone.utc).isoformat()
        )


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _cleanup_rate_limit_records(connection):
    """Remove expired rate-limit keys using backend-compatible SQL."""
    if connection.dialect.name == "postgresql":
        cutoff_expression = "CURRENT_TIMESTAMP - INTERVAL '2 hours'"
    else:
        cutoff_expression = "datetime('now', '-2 hours')"

    for table_name in (
        "registration_rate_limits",
        "login_rate_limits",
        "contact_rate_limits",
        "subscribe_rate_limits",
    ):
        connection.execute(
            text(
                f"DELETE FROM {table_name} "
                f"WHERE window_started_at < {cutoff_expression}"
            )
        )


def _env_flag(name, default=False):
    """Parse a boolean environment variable without treating '0' as true."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def init_db():
    """Bootstrap local/dev databases and compatibility tables.

    Production deployments should run the canonical Alembic migrations instead
    of calling SQLAlchemy create_all(), which can otherwise leave the schema
    ahead of Alembic's revision history.
    """
    from models import User, Website, Message, Subscriber  # noqa: F401

    auto_create = _env_flag("AUTO_CREATE_DB", default=not _env_flag("RENDER"))
    if auto_create:
        Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS registration_rate_limits (
                    rate_key VARCHAR(255) PRIMARY KEY,
                    window_started_at TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_registration_rate_limits_window "
                "ON registration_rate_limits (window_started_at)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS login_rate_limits (
                    rate_key VARCHAR(255) PRIMARY KEY,
                    window_started_at TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_login_rate_limits_window "
                "ON login_rate_limits (window_started_at)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS contact_rate_limits (
                    rate_key VARCHAR(255) PRIMARY KEY,
                    window_started_at TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_contact_rate_limits_window "
                "ON contact_rate_limits (window_started_at)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS subscribe_rate_limits (
                    rate_key VARCHAR(255) PRIMARY KEY,
                    window_started_at TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_subscribe_rate_limits_window "
                "ON subscribe_rate_limits (window_started_at)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_websites_owner_id_id_desc "
                "ON websites (owner_id, id DESC)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(64) NOT NULL UNIQUE,
                    expires_at TIMESTAMPTZ NOT NULL,
                    used_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id "
                "ON password_reset_tokens (user_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_expires_at "
                "ON password_reset_tokens (expires_at)"
            )
        )

        if connection.dialect.name == "sqlite":
            payments_table_exists = connection.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'payments'"
                )
            ).scalar() is not None
            if payments_table_exists:
                connection.execute(
                    text(
                        """
                        CREATE TRIGGER IF NOT EXISTS prevent_paid_payment_downgrade
                        BEFORE UPDATE OF status ON payments
                        FOR EACH ROW
                        WHEN OLD.status = 'paid'
                             AND NEW.status IN ('pending', 'initiated', 'failed', 'cancelled')
                        BEGIN
                            SELECT RAISE(ABORT, 'paid payment cannot be downgraded');
                        END
                        """
                    )
                )

        _cleanup_rate_limit_records(connection)
        connection.execute(text("SELECT 1"))

    print(
        "Database initialized successfully using "
        f"{engine.url.get_backend_name()} (auto_create={auto_create})"
    )
