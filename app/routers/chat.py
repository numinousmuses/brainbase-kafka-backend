# app/routers/chat.py
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat import Chat
from app.schemas.chat import ChatNewResponse
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

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
    chat_id = str(uuid.uuid4())
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

@router.delete("/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    """
    Delete the chat identified by `chat_id`.
    
    Returns a message indicating successful deletion.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
         raise HTTPException(status_code=404, detail="Chat not found.")
    db.delete(chat)
    db.commit()
    return {"detail": "Chat deleted successfully."}

@router.patch("/rename", response_model=ChatNewResponse)
def rename_chat(
    chat_id: str = Form(...),
    new_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Rename an existing chat.
    
    - **chat_id**: The ID of the chat to rename.
    - **new_name**: The new name for the chat.
    
    Updates the `last_updated` field to the current UTC timestamp.
    
    Returns:
      - **chat_id**: The chat's ID.
      - **name**: The updated chat name.
      - **last_updated**: The updated timestamp as an ISO 8601 string.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
         raise HTTPException(status_code=404, detail="Chat not found.")
    
    chat.name = new_name
    chat.last_updated = datetime.utcnow().isoformat()
    
    db.commit()
    db.refresh(chat)
    
    return ChatNewResponse(
        chat_id=chat.id,
        name=chat.name,
        last_updated=chat.last_updated
    )