# app/routers/chat.py
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat import Chat
from app.schemas.chat import ChatNewResponse

router = APIRouter()

@router.post("/new", response_model=ChatNewResponse)
def create_chat(
    user_id: str = Form(...),
    workspace_id: str = Form(...),
    chat_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Create a new chat with the provided chat name, user ID, and workspace ID.
    
    - **user_id**: The ID of the user creating the chat.
    - **workspace_id**: The ID of the workspace where the chat belongs.
    - **chat_name**: The desired name for the new chat.
    
    The `last_updated` field is initialized to the current UTC timestamp.
    
    Returns:
      - **chat_id**: The generated UUID for the new chat.
      - **name**: The name of the chat.
      - **last_updated**: The current timestamp as an ISO 8601 string.
    """
    # Generate a new UUID for the chat
    chat_id = str(uuid.uuid4())
    # Use the current UTC time as an ISO 8601 formatted string
    current_timestamp = datetime.utcnow().isoformat()

    new_chat = Chat(
        id=chat_id,
        name=chat_name,
        last_updated=current_timestamp,
        user_id=user_id,
        workspace_id=workspace_id
    )
    
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    return ChatNewResponse(
        chat_id=new_chat.id,
        name=new_chat.name,
        last_updated=new_chat.last_updated
    )
