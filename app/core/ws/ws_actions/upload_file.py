import os
import base64
import uuid

from fastapi import WebSocket
from sqlalchemy.orm import Session

from schemas.ws import ChatMessage
from app.models.chat_file import ChatFile
from app.models.file import File as FileModel
from app.models.chat import Chat


async def handle_upload_file(
    db: Session,
    websocket: WebSocket,
    message_data: dict,
    conversation_objs: list,
    chat: Chat
):
    """
    Handle 'upload_file' action. 
    Frontend sends:
    {
      "action": "upload_file",
      "filename": "some.pdf",
      "file_data": "base64-encoded content..."
    }
    We decode, save the file, create ChatFile + File if needed, 
    then add a message to the conversation.
    """
    filename = message_data.get("filename")
    file_data_b64 = message_data.get("file_data")
    if not filename or not file_data_b64:
        await websocket.send_json({"error": "Missing filename or file_data."})
        return

    file_bytes = base64.b64decode(file_data_b64)
    file_id = str(uuid.uuid4())
    unique_filename = f"{file_id}_{filename}"
    file_path = os.path.join("uploads/files", unique_filename)

    # Save file to disk
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Create a record in ChatFile for this chat
    new_chat_file = ChatFile(
        id=file_id,
        filename=filename,
        path=file_path,
        chat_id=chat.id
    )
    db.add(new_chat_file)

    # Also add the file to the workspace's File table if not already present
    existing_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not existing_file:
        new_file = FileModel(
            id=file_id,
            filename=filename,
            path=file_path,
            workspace_id=chat.workspace_id
        )
        db.add(new_file)
    db.commit()

    # Add a 'file' message to conversation
    file_message = ChatMessage(
        role="user",
        type="file",
        content={
            "file_id": file_id,
            "filename": filename,
            "path": file_path
        }
    )
    conversation_objs.append(file_message)
    await websocket.send_json({"action": "file_uploaded", "message": file_message})