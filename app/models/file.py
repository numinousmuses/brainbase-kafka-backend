# app/models/file.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class File(Base):
    __tablename__ = "files"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)  # Local filesystem path
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    
    # Relationship
    workspace = relationship("Workspace", back_populates="files")
