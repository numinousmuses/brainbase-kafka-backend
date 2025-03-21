# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # only needed for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# ADD THIS:
def get_db():
    """
    Yields a database session for FastAPI dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()