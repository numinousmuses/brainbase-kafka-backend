# app/routers/chat.py
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat import Chat
from app.schemas.chat import ChatNewResponse
import os
import uuid
import json
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
import PyPDF2

from app.models.chat_file import ChatFile
from app.models.chat_conversation import ChatConversation
from app.models.file import File as FileModel

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
    chat_files_data = []
    for file in chat_files:
        chat_files_data.append({
            "file_id": file.id,
            "filename": file.filename,
            "path": file.path
        })

    # Parse text content from chat files that are PDFs or text files.
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

    # Load workspace files that are not attached to this chat.
    workspace_files_all = db.query(FileModel).filter(FileModel.workspace_id == chat.workspace_id).all()
    chat_file_ids = set(cf.id for cf in chat_files)
    workspace_files_not_in_chat = []
    for wf in workspace_files_all:
        if wf.id not in chat_file_ids:
            workspace_files_not_in_chat.append({
                "file_id": wf.id,
                "filename": wf.filename,
                "path": wf.path
            })

    # Load AI model configurations (placeholder).
    models = {}

    # Send initial data to the client.
    initial_payload = {
        "chat_id": chat_id,
        "conversation": conversation,
        "chat_files": chat_files_data,
        "parsed_files": parsed_files,
        "workspace_files": workspace_files_not_in_chat,
        "models": models
    }
    await websocket.send_json(initial_payload)

    # This list will hold new messages (including file upload messages) for later persistence.
    new_messages = []

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message_data = json.loads(raw_data)
            except Exception:
                message_data = None

            # If the message is a JSON with an action field, handle specific actions.
            if message_data and "action" in message_data:
                action = message_data["action"]
                if action == "upload_file":
                    # Expecting keys: filename and file_data (base64-encoded).
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

                # Generate a simple echo response for now (to be replaced with LLM generation later).
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
                content=str(msg["content"])  # Convert content to string if necessary.
            )
            db.add(new_msg)
        db.commit()