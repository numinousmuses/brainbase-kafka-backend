# app/models/chat_file_version.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class ChatFileVersion(Base):
    __tablename__ = "chat_file_versions"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    chat_file_id = Column(String, ForeignKey("chat_files.id"), nullable=False)
    timestamp = Column(String, nullable=False)  # You may switch to DateTime later
    content = Column(String, nullable=False)  # Content of the .based file
    
    # Relationship
    chat_file = relationship("ChatFile", back_populates="versions")
