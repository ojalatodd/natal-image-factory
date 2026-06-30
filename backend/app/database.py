from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite needs check_same_thread=False when used across threads (API + sync calls).
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. For MVP we use create_all; Alembic migrations land in hardening."""
    from app import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)

    # Lightweight migration: add columns if missing (pre-existing databases)
    if settings.database_url.startswith("sqlite"):
        import sqlalchemy as sa
        with engine.connect() as conn:
            user_cols = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))]
            if "role" not in user_cols:
                conn.execute(sa.text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
                conn.commit()
            job_cols = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(jobs)"))]
            if "celery_task_id" not in job_cols:
                conn.execute(sa.text("ALTER TABLE jobs ADD COLUMN celery_task_id VARCHAR"))
                conn.commit()
