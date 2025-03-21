# app/routers/ws_disconnect.py
import json
import uuid
from fastapi import WebSocket
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.chat_conversation import ChatConversation
from schemas.ws import ChatMessage

async def persist_on_disconnect(
    db: Session, 
    chat_id: str, 
    conversation_objs: list,
    websocket: WebSocket
):
    """
    On WebSocketDisconnect, we persist conversation changes to ChatConversation in the DB,
    then close the WebSocket.

    :param db: An active SQLAlchemy Session
    :param chat_id: The UUID/string of the Chat
    :param conversation_objs: A list of ChatMessage objects (in-memory)
    :param websocket: The active WebSocket connection
    """

    # 1) Convert in-memory conversation messages → DB rows
    for msg in conversation_objs:
        # If you track which messages are 'new' vs. 'existing', you could skip stored ones.
        # This example stores everything again. In practice, you might store only new messages.
        db_message = ChatConversation(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=msg.role,
            type=msg.type,
            content=(
                # If content is a dict, store JSON; else store as string
                json.dumps(msg.content) if isinstance(msg.content, dict) else str(msg.content)
            )
        )
        db.add(db_message)

    # 2) Commit changes
    db.commit()

    # 3) Optionally close the DB session
    db.close()

    # 4) Close the websocket
    await websocket.close()