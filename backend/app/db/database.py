import os
from pathlib import Path
import backend.app.core.config  # Loads .env
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQLITE_DB_PATH = PROJECT_ROOT / "bankassist.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:razak5056@localhost:5432/bankassist_db"
)

# Connect args if using SQLite
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args=connect_args,
    )
    # Validate connection quickly
    with engine.connect() as conn:
        pass
except Exception:
    # Fallback to local SQLite database when PostgreSQL is not running
    DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# Database session dependency
def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
