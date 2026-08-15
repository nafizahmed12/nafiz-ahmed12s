import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url():
    """Return the configured database URL.

    Render should provide DATABASE_URL for the deployed application.
    SQLite is intentionally kept only for local development when explicitly
    requested with USE_SQLITE=1.
    """
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
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    # Import here to avoid circular imports while Base is being defined.
    from models import User, Website  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Fail at startup if the configured PostgreSQL connection is unusable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print(f"Database initialized successfully using {engine.url.get_backend_name()}")
