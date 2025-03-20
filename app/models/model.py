# app/models/model.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Model(Base):
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, index=True)  # UUID as string
    name = Column(String, nullable=False)
    ak = Column(String, nullable=False)
    base_url = Column(String, nullable=False)  # Base URL for the OpenAI client
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="models")
