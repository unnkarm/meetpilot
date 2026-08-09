from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

raw_url = getattr(settings, "DATABASE_URL", None)
if raw_url and isinstance(raw_url, str) and "://" in raw_url:
    db_url = raw_url
else:
    db_url = "sqlite:///:memory:"

try:
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
except Exception:
    engine = create_engine("sqlite:///:memory:", future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
