# app/models/chat_file.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class ChatFile(Base):
    __tablename__ = "chat_files"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)  # Local filesystem path for the chat-specific file
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    
    # Relationships
    chat = relationship("Chat", back_populates="chat_files")
    versions = relationship("ChatFileVersion", back_populates="chat_file", cascade="all, delete-orphan")
