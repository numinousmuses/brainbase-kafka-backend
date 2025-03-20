# app/schemas/chat.py
from pydantic import BaseModel

class ChatNewResponse(BaseModel):
    chat_id: str
    name: str
    last_updated: str