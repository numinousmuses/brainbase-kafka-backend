# app/models/workspace.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(String, primary_key=True, index=True)  # Use a UUID string
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="workspaces")
    files = relationship("File", back_populates="workspace", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="workspace", cascade="all, delete-orphan")
