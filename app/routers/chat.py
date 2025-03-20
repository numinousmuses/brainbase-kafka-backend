# app/routers/chat.py
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

router = APIRouter()

class ChatMessage(BaseModel):
    sender: str
    message: str

@router.get("/")
async def list_chats():
    # Return a list of chats
    return [{"id": "chat1", "title": "General Chat"}]

# Example WebSocket endpoint for chat communication
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
