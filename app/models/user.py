# app/models/user.py
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)   # Use a UUID string
    email = Column(String, unique=True, nullable=False)
    
    # Relationships
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="user", cascade="all, delete-orphan")
