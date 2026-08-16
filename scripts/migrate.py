"""Safe production migration entrypoint.

Existing databases created before Alembic are stamped at the initial revision
instead of being recreated. Fresh databases run the initial migration normally.
"""

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import engine  # noqa: E402


def main() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    # If the application's existing schema is already present, establish the
    # Alembic baseline without attempting to recreate production tables.
    core_tables = {"users", "websites", "messages", "subscribers"}
    if core_tables.issubset(tables) and "alembic_version" not in tables:
        command.stamp(config, "0001_initial_schema")
        print("Existing database detected; Alembic baseline stamped safely.")
    else:
        command.upgrade(config, "head")
        print("Alembic migrations applied successfully.")


if __name__ == "__main__":
    main()
