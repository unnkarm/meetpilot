"""Legacy schema bootstrap for databases predating a complete baseline migration.

Run this once before Alembic on an empty local database. Existing tables are
left untouched; Alembic applies all subsequent schema changes.
"""

from sqlalchemy import text

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine


def bootstrap_schema() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    bootstrap_schema()
