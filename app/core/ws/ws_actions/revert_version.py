import json
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy.orm import Session

from schemas.ws import ChatMessage
from app.models.chat_file_version import ChatFileVersion
from app.models.chat_file import ChatFile
from app.models.chat import Chat


async def handle_revert_version(
    db: Session,
    websocket: WebSocket,
    message_data: dict,
    conversation_objs: list,
    chat: Chat
):
    """
    The frontend should send:
    {
        "action": "revert_version",
        "version_id": "...",
        "filename": "..."  # or ID
    }

    Steps:
    1) Find the older ChatFileVersion
    2) Create a new ChatFileVersion with same content
    3) Update chat.last_updated
    4) Return agent_response with new content
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
    chat_file = db.query(ChatFile).filter(ChatFile.filename == filename).first()
    if not chat_file:
        await websocket.send_json({"error": f"No .based file found for filename={filename}"})
        return

    # 3) Create new ChatFileVersion
    new_version_id = str(uuid.uuid4())
    revert_version = ChatFileVersion(
        id=new_version_id,
        chat_file_id=chat_file.id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=old_version.content
    )
    db.add(revert_version)

    # Update chat.last_updated
    chat.last_updated = datetime.now(timezone.utc).isoformat()
    db.commit()

    # 4) Return updated .based file info
    agent_response = {
        "role": "assistant",
        "type": "file",
        "content": {
            "based_filename": chat_file.filename,
            "based_content": old_version.content,
            "message": f"Reverted to version {version_id}; new version is {new_version_id}"
        }
    }

    # Optionally log to conversation
    conversation_objs.append(
        ChatMessage(
            role="assistant",
            type="file",
            content=json.dumps({
                "based_filename": chat_file.filename,
                "based_content": old_version.content,
                "revert_notice": f"Reverted from version {version_id}"
            })
        )
    )

    await websocket.send_json({"action": "revert_complete", "message": agent_response})