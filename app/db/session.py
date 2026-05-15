from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False)


def get_engine():
    global engine
    if engine is None:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_error_message(error: Exception) -> str:
    if isinstance(error, (ImportError, ModuleNotFoundError)):
        return "Database driver is not installed. Run: pip install -r requirements.txt"
    if isinstance(error, SQLAlchemyError):
        return "Database is not available. Check DATABASE_URL and run: alembic upgrade head"
    return "Database is not available. Check configuration and migrations."
