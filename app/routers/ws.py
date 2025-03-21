# app/routers/ws.py
import os
import uuid
import json
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
import PyPDF2

from schemas.ws import (
    WsInitialPayload,
    ChatMessage,
    ChatFileText,
    ChatFileBased,
    ChatFileBasedVersion,
    WorkspaceFile
)

import app.core.unifieddiff as unifieddiff
from app.core.database import get_db
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.models.chat_conversation import ChatConversation
from app.models.chat_file_version import ChatFileVersion
from app.models.file import File as FileModel
from app.models.model import Model as ModelModel
from app.core.basedagent import handle_new_message

router = APIRouter()

@router.websocket("/ws/{chat_id}")
async def chat_ws(websocket: WebSocket, chat_id: str):
    await websocket.accept()

    db: Session = next(get_db())

    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        await websocket.send_json({"error": "Chat not found."})
        await websocket.close()
        return

    # Convert DB conversation -> List[ChatMessage]
    conversation_objs = []
    if chat.conversation:
        for msg in chat.conversation:
            conversation_objs.append(
                ChatMessage(
                    role=msg.role,
                    type=msg.type,
                    content=msg.content
                )
            )

    # Load and partition chat files
    chat_files = db.query(ChatFile).filter(ChatFile.chat_id == chat_id).all()

    parsed_files = {}
    for file in chat_files:
        fname = file.filename.lower()
        if fname.endswith(".txt"):
            try:
                with open(file.path, "r", encoding="utf-8") as f:
                    parsed_text = f.read()
            except Exception:
                parsed_text = ""
            parsed_files[file.id] = parsed_text
        elif fname.endswith(".pdf"):
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

    chat_files_text_objs = []
    chat_files_based_objs = []

    for file in chat_files:
        ext = file.filename.lower().rsplit(".", 1)[-1]
        if ext == "based":
            versions = (
                db.query(ChatFileVersion)
                .filter(ChatFileVersion.chat_file_id == file.id)
                .order_by(ChatFileVersion.timestamp)
                .all()
            )
            if versions:
                latest_version = versions[-1]
                version_objs = []
                for ver in versions:
                    diff_patch = ""
                    if ver.id != latest_version.id:
                        diff_patch = unifieddiff.make_patch(ver.content, latest_version.content)
                    version_objs.append(
                        ChatFileBasedVersion(
                            version_id=ver.id,
                            timestamp=str(ver.timestamp),
                            diff=diff_patch
                        )
                    )
                latest_content = latest_version.content
            else:
                version_objs = []
                latest_content = ""

            chat_files_based_objs.append(
                ChatFileBased(
                    file_id=file.id,
                    name=file.filename,
                    latest_content=latest_content,
                    versions=version_objs,
                    type="based"
                )
            )
        else:
            if ext in ["jpg", "jpeg", "png", "gif"]:
                file_type = "image"
                content = file.path
            else:
                file_type = "text"
                content = parsed_files.get(file.id, "")

            chat_files_text_objs.append(
                ChatFileText(
                    file_id=file.id,
                    name=file.filename,
                    content=content,
                    type=file_type
                )
            )

    # Workspace files not attached to this chat & not .based
    workspace_files_all = db.query(FileModel).filter(FileModel.workspace_id == chat.workspace_id).all()
    chat_file_ids = set(cf.id for cf in chat_files)
    workspace_files_objs = []
    for wf in workspace_files_all:
        if wf.id not in chat_file_ids and not wf.filename.lower().endswith(".based"):
            workspace_files_objs.append(
                WorkspaceFile(
                    file_id=wf.id,
                    name=wf.filename
                )
            )

    # Load model names
    models_query = db.query(ModelModel).filter(ModelModel.user_id == chat.user_id).all()
    model_names = [m.name for m in models_query]

    # Construct typed WsInitialPayload
    initial_payload_obj = WsInitialPayload(
        chat_id=str(chat_id),
        conversation=conversation_objs,
        chat_files_text=chat_files_text_objs,
        chat_files_based=chat_files_based_objs,
        workspace_files=workspace_files_objs,
        workspace_id=str(chat.workspace_id),
        models=model_names
    )
    # Send the typed payload as JSON
    await websocket.send_json(initial_payload_obj.dict())

    # We'll keep new_messages as a list of dict, 
    # but it could also be a list of ChatMessage objects if desired.
    new_messages = []

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message_data = json.loads(raw_data)
            except Exception:
                message_data = None

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
                    await websocket.send_json({"action": "file_uploaded", "message": file_message})
                elif action == "new_message":
                    model_name = message_data.get("model", "default_model")
                    prompt = message_data.get("prompt", "")
                    is_first_prompt = message_data.get("is_first_prompt", False)
                    is_chat_or_composer = message_data.get("is_chat_or_composer", False)
                    selected_filename = message_data.get("selected_filename", None)

                    model_obj = db.query(ModelModel).filter(ModelModel.name == model_name).first()
                    if not model_obj:
                        await websocket.send_json({"error": "Model not found."})
                        continue
                    model_ak = model_obj.ak
                    model_base_url = model_obj.base_url

                    # Separate out the selected based file and the rest
                    selected_based_file = None
                    other_based_files = []
                    for bf in chat_files_based_objs:
                        if selected_filename and bf.name == selected_filename:
                            selected_based_file = bf.dict()  # Convert pydantic to dict
                        else:
                            other_based_files.append(bf.dict())

                    if selected_based_file is None:
                        other_based_files = [bf.dict() for bf in chat_files_based_objs]

                    result = handle_new_message(
                        model_name, 
                        model_ak, 
                        model_base_url, 
                        selected_filename, 
                        selected_based_file,  # dict
                        prompt, 
                        is_first_prompt, 
                        is_chat_or_composer, 
                        [cm.dict() for cm in conversation_objs], 
                        [cft.dict() for cft in chat_files_text_objs], 
                        other_based_files
                    )

                    # Process result
                    if result["type"] in ["based", "diff"]:
                        based_filename = result.get("based_filename", "unknown.based")
                        agent_response = {
                            "role": "assistant",
                            "type": "file",
                            "content": {
                                "based_filename": based_filename,
                                "based_content": result["output"]
                            }
                        }
                        new_messages.append(agent_response)
                        conversation_objs.append(
                            ChatMessage(
                                role="assistant",
                                type="file",
                                content=json.dumps({
                                    "based_filename": based_filename,
                                    "based_content": result["output"]
                                })
                            )
                        )
                        await websocket.send_json({"action": "agent_response", "message": agent_response})
                    elif result["type"] == "response":
                        agent_response = {
                            "role": "assistant",
                            "type": "text",
                            "content": result.get("message", result["output"])
                        }
                        new_messages.append(agent_response)
                        conversation_objs.append(
                            ChatMessage(
                                role="assistant",
                                type="text",
                                content=agent_response["content"]
                            )
                        )
                        await websocket.send_text(agent_response["content"])
                    else:
                        await websocket.send_json({"error": "Unknown response type from agent."})
                else:
                    await websocket.send_json({"error": "Unknown action."})
            else:
                # Treat as a plain text chat message.
                user_message = ChatMessage(
                    role="user",
                    type="text",
                    content=raw_data
                )
                new_messages.append(user_message.dict())
                conversation_objs.append(user_message)

                response_text = f"Echo: {raw_data}"
                assistant_message = ChatMessage(
                    role="assistant",
                    type="text",
                    content=response_text
                )
                new_messages.append(assistant_message.dict())
                conversation_objs.append(assistant_message)
                await websocket.send_text(response_text)

    except WebSocketDisconnect:
        # Persist new_messages to DB
        for msg_dict in new_messages:
            role = msg_dict["role"]
            msg_type = msg_dict["type"]
            content = json.dumps(msg_dict["content"]) if isinstance(msg_dict["content"], dict) else str(msg_dict["content"])
            new_msg = ChatConversation(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=role,
                type=msg_type,
                content=content
            )
            db.add(new_msg)
        db.commit()
