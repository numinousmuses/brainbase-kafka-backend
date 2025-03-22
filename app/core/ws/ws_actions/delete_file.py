# delete_file.py

import os
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.schemas.ws import ChatMessage
from app.models.chat_file import ChatFile
from app.models.file import File as FileModel
from app.models.chat import Chat
import json

async def handle_delete_file(
    db: Session,
    websocket: WebSocket,
    message_data: dict,
    conversation_objs: list,
    chat: Chat
):
    """
    Handle 'delete_file' action.
    
    Expected client message structure:
    {
      "action": "delete_file",
      "file_id": "<UUID or string>"
    }

    This removes the specified file from:
      - The ChatFile table (for the current chat),
      - The workspace's File table (if present),
      - The filesystem (if you want to delete the actual file),
    and adds a system-level conversation message confirming the deletion.
    """
    file_id = message_data.get("file_id")
    if not file_id:
        await websocket.send_json({"error": "Missing file_id for delete_file."})
        return

    # 1) Look up the ChatFile for this chat.
    chat_file = db.query(ChatFile).filter(ChatFile.id == file_id, ChatFile.chat_id == chat.id).first()
    if not chat_file:
        await websocket.send_json({"error": f"No file found for file_id={file_id} in this chat."})
        return
    
    # 2) Optionally remove the file from disk.
    file_path = chat_file.path
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Optionally handle/log the error; for now, we continue
        pass

    # 3) Remove the record from ChatFile (this file is no longer attached to the chat).
    db.delete(chat_file)

    # 4) Also remove the file from the workspace's File table, if it exists there.
    workspace_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if workspace_file:
        db.delete(workspace_file)

    # 5) Commit the changes.
    db.commit()

    # 6) Add a "system" message to the in-memory conversation to note the deletion.
    deletion_message = ChatMessage(
        role="system",
        type="file",
        content=f"""{chat_file.filename} was deleted."""
    )
    conversation_objs.append(deletion_message)

    # 7) Let the client know the file was deleted.
    await websocket.send_json({
        "action": "file_deleted",
        "message": deletion_message.dict()
    })