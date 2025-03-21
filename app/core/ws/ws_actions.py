# app/routers/ws_actions.py
import json
import uuid
import os
from datetime import datetime, timezone
from fastapi import WebSocket
from sqlalchemy.orm import Session
import base64

from schemas.ws import ChatMessage, ChatFileBasedVersion
from app.core.basedagent import handle_new_message
from app.models.chat_file import ChatFile
from app.models.chat_file_version import ChatFileVersion
from app.models.file import File as FileModel
from app.models.model import Model as ModelModel
from app.models.chat import Chat
import app.core.unifieddiff as unifieddiff


async def handle_action(
    db: Session, 
    websocket: WebSocket, 
    raw_data: str, 
    conversation_objs: list, 
    chat: Chat,
    chat_files_based_objs: list,
    chat_files_text_objs: list
):
    """
    Reads raw_data, parses JSON, checks 'action' key, and calls the appropriate sub-function.
    If no action is given, we treat it as plain text.
    """

    try:
        message_data = json.loads(raw_data)
    except Exception:
        message_data = None

    if not message_data or "action" not in message_data:
        # treat as plain text
        await handle_plain_text(raw_data, conversation_objs, websocket)
        return

    action = message_data["action"]
    if action == "upload_file":
        await handle_upload_file(db, websocket, message_data, conversation_objs, chat)
    elif action == "new_message":
        await handle_new_message_action(
            db,
            websocket,
            message_data,
            conversation_objs,
            chat,
            chat_files_based_objs,
            chat_files_text_objs
        )
    elif action == "revert_version":
        await handle_revert_version(db, websocket, message_data, conversation_objs, chat)
    else:
        await websocket.send_json({"error": f"Unknown action: {action}"})


async def handle_plain_text(raw_data: str, conversation_objs: list, websocket: WebSocket):
    """
    If no 'action' is provided, handle as a plain text user message.
    """
    user_message = ChatMessage(
        role="user",
        type="text",
        content=raw_data
    )
    conversation_objs.append(user_message)

    # Echo response
    response_text = f"Echo: {raw_data}"
    assistant_message = ChatMessage(
        role="assistant",
        type="text",
        content=response_text
    )
    conversation_objs.append(assistant_message)
    await websocket.send_text(response_text)


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


async def handle_new_message_action(
    db: Session,
    websocket: WebSocket,
    message_data: dict,
    conversation_objs: list,
    chat: Chat,
    chat_files_based_objs: list,
    chat_files_text_objs: list
):
    """
    Handle 'new_message' action.
    We read the user input, create a user_message in the conversation,
    call handle_new_message(...) from app.core.basedagent,
    and process the agent result.
    """
    model_name = message_data.get("model", "default_model")
    prompt = message_data.get("prompt", "")
    is_first_prompt = message_data.get("is_first_prompt", False)
    is_chat_or_composer = message_data.get("is_chat_or_composer", False)
    selected_filename = message_data.get("selected_filename", None)

    # Add the user message to conversation
    user_message = ChatMessage(
        role="user",
        type="text",
        content=prompt
    )
    conversation_objs.append(user_message)

    # Find the model
    model_obj = db.query(ModelModel).filter(ModelModel.name == model_name).first()
    if not model_obj:
        await websocket.send_json({"error": "Model not found."})
        return

    model_ak = model_obj.ak
    model_base_url = model_obj.base_url

    # Identify the selected .based file, if any, and the "other" based files
    selected_based_file_obj = None
    other_based_files_dict = []
    for bf_obj in chat_files_based_objs:
        if selected_filename and bf_obj.name == selected_filename:
            selected_based_file_obj = bf_obj
        else:
            other_based_files_dict.append(bf_obj.dict())

    # If no file was explicitly selected, treat all as 'other'
    if not selected_based_file_obj:
        other_based_files_dict = [bf_obj.dict() for bf_obj in chat_files_based_objs]

    selected_based_file_dict = selected_based_file_obj.dict() if selected_based_file_obj else None

    # 1) Call handle_new_message
    result = handle_new_message(
        model_name,
        model_ak,
        model_base_url,
        selected_filename,
        selected_based_file_dict,
        prompt,
        is_first_prompt,
        is_chat_or_composer,
        [cm.dict() for cm in conversation_objs],   # conversation
        [cft.dict() for cft in chat_files_text_objs],
        other_based_files_dict
    )

    # 2) Process agent result
    if result["type"] == "response":
        # Plain text response from agent
        agent_response = {
            "role": "assistant",
            "type": "text",
            "content": result.get("message", result["output"])
        }
        conversation_objs.append(ChatMessage(agent_response))

        # Update chat.last_updated
        chat.last_updated = datetime.now(timezone.utc).isoformat()
        db.commit()

        # Return text to client
        await websocket.send_text(agent_response["content"])

    elif result["type"] == "based":
        # A brand-new .based file was created
        based_filename = result.get("based_filename", "new_based_file.based")
        file_content = result["output"]

        new_based_file_id = str(uuid.uuid4())
        new_chat_file = ChatFile(
            id=new_based_file_id,
            filename=based_filename,
            path="(in-memory)",
            chat_id=chat.id
        )
        db.add(new_chat_file)

        new_version_id = str(uuid.uuid4())
        new_chat_file_version = ChatFileVersion(
            id=new_version_id,
            chat_file_id=new_based_file_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=file_content
        )
        db.add(new_chat_file_version)

        chat.last_updated = datetime.now(timezone.utc).isoformat()
        db.commit()

        agent_response = {
            "role": "assistant",
            "type": "file",
            "content": {
                "based_filename": based_filename,
                "based_content": file_content
            }
        }

        new_convo_block = ChatMessage(
            role="assistant",
            type="file",
            content=json.dumps({
                "based_filename": based_filename,
                "based_content": file_content
            })
        )
        conversation_objs.append(new_convo_block)
        await websocket.send_json({"action": "agent_response", "message": agent_response, "block": new_convo_block})

    elif result["type"] == "diff":
        # We have a diff for an existing .based file
        if not selected_based_file_obj:
            await websocket.send_json({"error": "No selected .based file to apply diff."})
            return

        diff_text = result["output"]
        chat_file_id = selected_based_file_obj.file_id
        existing_chat_file = db.query(ChatFile).filter(ChatFile.id == chat_file_id).first()
        if not existing_chat_file:
            await websocket.send_json({"error": f"ChatFile not found for id={chat_file_id}"})
            return

        latest_version_db = (
            db.query(ChatFileVersion)
            .filter(ChatFileVersion.chat_file_id == chat_file_id)
            .order_by(ChatFileVersion.timestamp.desc())
            .first()
        )
        if not latest_version_db:
            await websocket.send_json({"error": "No existing version found for this .based file."})
            return

        old_content = latest_version_db.content

        # Apply the diff
        try:
            new_content = unifieddiff.apply_patch(old_content, diff_text)
        except Exception as e:
            await websocket.send_json({"error": f"Applying diff failed: {str(e)}"})
            return

        # Create a new version
        new_version_id = str(uuid.uuid4())
        new_version = ChatFileVersion(
            id=new_version_id,
            chat_file_id=chat_file_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=new_content
        )
        db.add(new_version)

        # Optionally recompute older diffs
        older_diffs = []
        all_versions = (
            db.query(ChatFileVersion)
            .filter(ChatFileVersion.chat_file_id == chat_file_id)
            .order_by(ChatFileVersion.timestamp)
            .all()
        )
        for ver in all_versions:
            if ver.id != new_version.id:
                patch_diff = unifieddiff.make_patch(ver.content, new_version.content)
                older_diffs.append({
                    "version_id": ver.id,
                    "diff": patch_diff
                })

        # Update chat.last_updated
        chat.last_updated = datetime.now(timezone.utc).isoformat()
        db.commit()

        agent_response = {
            "role": "assistant",
            "type": "file",
            "content": {
                "based_filename": selected_based_file_obj.name,
                "based_content": new_content
            }
        }

        conversation_objs.append(
            ChatMessage(
                role="assistant",
                type="file",
                content=json.dumps({
                    "based_filename": selected_based_file_obj.name,
                    "based_content": diff_text
                })
            )
        )
        await websocket.send_json({"action": "agent_response", "message": agent_response})
    else:
        await websocket.send_json({"error": "Unknown response type from agent."})


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
