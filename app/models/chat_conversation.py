# app/models/chat_conversation.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(String, nullable=False)
    
    # Relationship
    chat = relationship("Chat", back_populates="conversation")
