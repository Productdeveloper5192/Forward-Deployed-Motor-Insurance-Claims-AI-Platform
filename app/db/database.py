from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  ensures models are registered on Base

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """create_all() only creates tables that don't exist yet — it never alters an
    existing table. There's no Alembic here, so new nullable columns added to a
    model after the DB file was first created need a manual catch-up like this."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(claims)")}
        if "paid_at" not in existing:
            conn.exec_driver_sql("ALTER TABLE claims ADD COLUMN paid_at DATETIME")
