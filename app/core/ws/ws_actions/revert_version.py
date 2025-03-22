import json
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.schemas.ws import ChatMessage
from app.models.chat_file_version import ChatFileVersion
from app.models.chat_file import ChatFile
from app.models.chat import Chat
from app.models.chat_conversation import ChatConversation


async def handle_revert_version(
    db: Session,
    websocket: WebSocket,
    message_data: dict,
    conversation_objs: list,
    chat: Chat
):
    """
    Handles reverting a .based file to a previous version.
    """
    version_id = message_data.get("version_id")
    filename = message_data.get("filename")
    
    if not version_id or not filename:
        await websocket.send_json({"error": "Missing version_id or filename for revert_version."})
        return

    # 1) Find older version
    old_version = db.query(ChatFileVersion).filter(ChatFileVersion.id == version_id).first()
    if not old_version:
        await websocket.send_json({"error": f"No version found for version_id={version_id}"})
        return

    # 2) Find corresponding ChatFile by filename
    chat_file = db.query(ChatFile).filter(
        ChatFile.chat_id == str(chat.id),  # Make sure it belongs to this chat
        ChatFile.filename == filename
    ).first()
    
    if not chat_file:
        await websocket.send_json({"error": f"No .based file found for filename={filename}"})
        return

    # 3) Create new ChatFileVersion
    new_version_id = str(uuid.uuid4())
    current_time = datetime.now(timezone.utc)
    revert_version = ChatFileVersion(
        id=new_version_id,
        chat_file_id=chat_file.id,
        timestamp=current_time.isoformat(),
        content=old_version.content
    )
    db.add(revert_version)

    # 4) Update chat.last_updated
    chat.last_updated = current_time.isoformat()
    
    # 5) Add an entry to the chat conversation - Add UUID for the id field
    revert_message = {
        "based_filename": chat_file.filename,
        "based_content": old_version.content,
        "revert_notice": f"Reverted from version {version_id}"
    }
    
    conversation_entry = ChatConversation(
        id=str(uuid.uuid4()),  # Generate a new UUID for the ID
        chat_id=str(chat.id),
        role="assistant",
        type="file",
        content=json.dumps(revert_message)
    )
    db.add(conversation_entry)
    db.commit()

    # 6) Add revert note to conversation history
    conversation_objs.append(
        ChatMessage(
            role="assistant",
            type="file",
            content=json.dumps(revert_message)
        )
    )

    # 7) Send response to client
    agent_response = {
        "role": "assistant",
        "type": "file",
        "content": {
            "based_filename": chat_file.filename,
            "based_content": old_version.content,
            "message": f"Reverted to version from {old_version.timestamp}."
        }
    }

    await websocket.send_json({
        "action": "revert_complete", 
        "message": agent_response
    })
