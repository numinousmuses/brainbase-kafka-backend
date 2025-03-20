# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.core.config import DATABASE_URL  # If you're storing DB URL in config.py

# Create the engine (for SQLite, we need 'check_same_thread=False' for multithreading)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """
    Initialize the database by creating all tables (if they don't already exist).
    """
    Base.metadata.create_all(bind=engine)
