import os

from sqlalchemy import create_engine, text
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
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    engine_options = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
    }

    if not url.startswith("sqlite"):
        engine_options.update({
            # Keep per-instance DB usage bounded so horizontal scaling does not
            # create an uncontrolled number of PostgreSQL connections.
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_use_lifo": True,
        })

    return create_engine(url, **engine_options)


engine = create_database_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db():
    # Import all models so SQLAlchemy creates every required table.
    from models import User, Website, Message, Subscriber  # noqa: F401

    Base.metadata.create_all(bind=engine)

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print(f"Database initialized successfully using {engine.url.get_backend_name()}")
