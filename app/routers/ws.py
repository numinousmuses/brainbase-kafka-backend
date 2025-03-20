# app/routers/chat.py
import os
import uuid
import json
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
import PyPDF2

# Import our diff functions from unifieddiff.py
import unifieddiff

from app.core.database import get_db
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.models.chat_conversation import ChatConversation
from app.models.chat_file_version import ChatFileVersion
from app.models.file import File as FileModel
from app.models.model import Model as ModelModel

router = APIRouter()

@router.websocket("/ws/{chat_id}")
async def chat_ws(websocket: WebSocket, chat_id: str):
    await websocket.accept()

    # Acquire a database session.
    db: Session = next(get_db())

    # Load the chat.
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        await websocket.send_json({"error": "Chat not found."})
        await websocket.close()
        return

    # Load existing conversation messages.
    conversation = []
    if chat.conversation:
        for msg in chat.conversation:
            conversation.append({
                "role": msg.role,
                "type": msg.type,
                "content": msg.content
            })

    # Load files attached to this chat.
    chat_files = db.query(ChatFile).filter(ChatFile.chat_id == chat_id).all()

    # Partition chat files into non-based and based files.
    chat_files_text = []    # Non-based files (text or images)
    chat_files_based = []   # Files with extension .based

    # For non-based files, also extract text if possible.
    parsed_files = {}
    for file in chat_files:
        fname = file.filename.lower()
        if fname.endswith('.txt'):
            try:
                with open(file.path, "r", encoding="utf-8") as f:
                    parsed_text = f.read()
            except Exception:
                parsed_text = ""
            parsed_files[file.id] = parsed_text
        elif fname.endswith('.pdf'):
            try:
                with open(file.path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    parsed_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            parsed_text += text
            except Exception:
                parsed_text = "[Error parsing PDF]"
            parsed_files[file.id] = parsed_text

    # Partition files.
    for file in chat_files:
        ext = file.filename.lower().rsplit('.', 1)[-1]
        if ext == "based":
            # For each .based file, load its version history.
            versions = db.query(ChatFileVersion).filter(
                ChatFileVersion.chat_file_id == file.id
            ).order_by(ChatFileVersion.timestamp).all()
            if versions:
                latest_version = versions[-1]
                versions_data = []
                # For each version, compute diff from that version to latest.
                for ver in versions:
                    diff_patch = ""
                    if ver.id != latest_version.id:
                        diff_patch = unifieddiff.make_patch(ver.content, latest_version.content)
                    versions_data.append({
                        "version_id": ver.id,
                        "timestamp": ver.timestamp,
                        "diff": diff_patch
                    })
            else:
                latest_version = None
                versions_data = []
            chat_files_based.append({
                "file_id": file.id,
                "name": file.filename,
                "latest_content": latest_version.content if latest_version else "",
                "versions": versions_data,
                "type": "based"
            })
        else:
            # For non-based files, decide type.
            if ext in ["jpg", "jpeg", "png", "gif"]:
                file_type = "image"
                content = file.path  # Client can load image from URL/path.
            else:
                file_type = "text"
                content = parsed_files.get(file.id, "")
            chat_files_text.append({
                "file_id": file.id,
                "name": file.filename,
                "content": content,
                "type": file_type
            })

    # Load workspace files that are not attached to this chat and are not .based.
    workspace_files_all = db.query(FileModel).filter(FileModel.workspace_id == chat.workspace_id).all()
    chat_file_ids = set(cf.id for cf in chat_files)
    workspace_files_not_in_chat = []
    for wf in workspace_files_all:
        if wf.id not in chat_file_ids:
            if not wf.filename.lower().endswith('.based'):
                workspace_files_not_in_chat.append({
                    "file_id": wf.id,
                    "name": wf.filename
                })

    # Load AI model configurations (for models belonging to the chat's user).
    models_query = db.query(ModelModel).filter(ModelModel.user_id == chat.user_id).all()
    model_names = [model.name for model in models_query]

    # Build the initial payload.
    initial_payload = {
        "chat_id": chat_id,
        "conversation": conversation,
        "chat_files_text": chat_files_text,
        "chat_files_based": chat_files_based,
        "workspace_files": workspace_files_not_in_chat,
        "workspace_id": chat.workspace_id,
        "models": model_names
    }
    await websocket.send_json(initial_payload)

    # List to hold new messages for later persistence.
    new_messages = []

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message_data = json.loads(raw_data)
            except Exception:
                message_data = None

            # Handle JSON messages with specific actions.
            if message_data and "action" in message_data:
                action = message_data["action"]
                if action == "upload_file":
                    # Expect keys: filename and file_data (base64-encoded).
                    filename = message_data.get("filename")
                    file_data_b64 = message_data.get("file_data")
                    if not filename or not file_data_b64:
                        await websocket.send_json({"error": "Missing filename or file_data."})
                        continue

                    file_bytes = base64.b64decode(file_data_b64)
                    file_id = str(uuid.uuid4())
                    unique_filename = f"{file_id}_{filename}"
                    file_path = os.path.join("uploads/files", unique_filename)

                    # Save file to disk.
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)

                    # Create a record in ChatFile for this chat.
                    new_chat_file = ChatFile(
                        id=file_id,
                        filename=filename,
                        path=file_path,
                        chat_id=chat_id
                    )
                    db.add(new_chat_file)

                    # Also add the file to the workspace's File table if not already present.
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

                    file_message = {
                        "role": "user",
                        "type": "file",
                        "content": {
                            "file_id": file_id,
                            "filename": filename,
                            "path": file_path
                        }
                    }
                    new_messages.append(file_message)
                    conversation.append(file_message)
                    await websocket.send_json({"action": "file_uploaded", "message": file_message})
                else:
                    await websocket.send_json({"error": "Unknown action."})
            else:
                # Treat as a plain text chat message.
                user_message = {
                    "role": "user",
                    "type": "text",
                    "content": raw_data
                }
                new_messages.append(user_message)
                conversation.append(user_message)

                # Generate an echo response (to be replaced with actual LLM generation later).
                response_text = f"Echo: {raw_data}"
                assistant_message = {
                    "role": "assistant",
                    "type": "text",
                    "content": response_text
                }
                new_messages.append(assistant_message)
                conversation.append(assistant_message)
                await websocket.send_text(response_text)
    except WebSocketDisconnect:
        # On disconnect, persist new messages to the database.
        for msg in new_messages:
            new_msg = ChatConversation(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=msg["role"],
                type=msg["type"],
                content=str(msg["content"])
            )
            db.add(new_msg)
        db.commit()
