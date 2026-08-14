import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url():
    """Return the configured database URL.

    Render/PostgreSQL can provide DATABASE_URL. For local development,
    SQLite remains available as a fallback so the project can still run
    before PostgreSQL is configured.
    """
    return os.getenv("DATABASE_URL", "sqlite:///messages.db")


def create_database_engine():
    url = get_database_url()

    # Some hosting providers expose postgres:// while SQLAlchemy expects
    # postgresql://.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)
