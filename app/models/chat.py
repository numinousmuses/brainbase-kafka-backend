# app/models/chat.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    name = Column(String, nullable=False)
    last_updated = Column(String)  # You might switch to DateTime later
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    workspace = relationship("Workspace", back_populates="chats")
    conversation = relationship("ChatConversation", back_populates="chat", cascade="all, delete-orphan")
    chat_files = relationship("ChatFile", back_populates="chat", cascade="all, delete-orphan")
