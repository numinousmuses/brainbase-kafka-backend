import json
import uuid
from fastapi import WebSocket
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.chat_conversation import ChatConversation
from app.schemas.ws import ChatMessage

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
    try:
        print(f"=== Persisting conversation for chat {chat_id} on disconnect ===")
        
        # 1) Delete existing conversations to avoid duplication
        print(f"Deleting existing conversation records for chat_id={chat_id}")
        db.query(ChatConversation).filter(ChatConversation.chat_id == chat_id).delete()
        
        # 2) Convert in-memory conversation messages to DB rows
        print(f"Converting {len(conversation_objs)} in-memory messages to DB records")
        for index, msg in enumerate(conversation_objs):
            # Extract fields properly depending on whether msg is a dict or object
            if hasattr(msg, 'role'):
                # It's an object with attributes
                role = msg.role
                content_type = msg.type
                content = msg.content
            else:
                # It's a dictionary
                role = msg.get('role')
                content_type = msg.get('type')
                content = msg.get('content')
                
            # Serialize content if needed
            if isinstance(content, dict):
                serialized_content = json.dumps(content)
            else:
                serialized_content = content
                
            # Create the DB record
            db_message = ChatConversation(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=role,
                type=content_type,
                content=serialized_content,
            )
            db.add(db_message)
            print(f"Added message {index+1}/{len(conversation_objs)}: role={role}, type={content_type}")
        
        # 3) Commit changes
        db.commit()
        print("Successfully committed conversation to database")
        
        # 4) Close the DB session
        db.close()
        print("Closed database session")
        
    except Exception as e:
        print(f"ERROR during conversation persistence: {str(e)}")
        # Try to rollback if there was an error
        try:
            db.rollback()
        except:
            pass
    finally:
        # 5) Close the websocket
        try:
            print("Closing WebSocket connection")
            await websocket.close()
        except Exception as e:
            print(f"Error closing websocket: {str(e)}")
