# app/routers/ws.py
import os
import uuid
import json
import base64
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
import PyPDF2
from pydantic import model_dump

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
    await websocket.send_json(model_dump(initial_payload_obj))


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

                    file_message = ChatMessage({
                        "role": "user",
                        "type": "file",
                        "content": {
                            "file_id": file_id,
                            "filename": filename,
                            "path": file_path
                        }
                    })
                    conversation_objs.append(file_message)
                    await websocket.send_json({"action": "file_uploaded", "message": file_message})
                elif action == "new_message":
                    model_name = message_data.get("model", "default_model")
                    prompt = message_data.get("prompt", "")
                    is_first_prompt = message_data.get("is_first_prompt", False)
                    is_chat_or_composer = message_data.get("is_chat_or_composer", False)
                    selected_filename = message_data.get("selected_filename", None)

                    # add the user message to the conversation

                    user_message = ChatMessage(
                        role="user",
                        type="text",
                        content=prompt
                    )
                    conversation_objs.append(user_message)

                    model_obj = db.query(ModelModel).filter(ModelModel.name == model_name).first()
                    if not model_obj:
                        await websocket.send_json({"error": "Model not found."})
                        continue
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

                    # If no file was explicitly selected, we treat all as 'other'
                    if not selected_based_file_obj:
                        other_based_files_dict = [bf_obj.dict() for bf_obj in chat_files_based_objs]

                    # Convert selected .based file to dict if found
                    selected_based_file_dict = selected_based_file_obj.dict() if selected_based_file_obj else None

                    # Call handle_new_message
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

                    ### Process the agent result
                    if result["type"] == "response":
                        #
                        # 1) Plain text response:
                        #    - Add to conversation
                        #    - Update chat.last_updated
                        #    - Return updated messages to frontend
                        #
                        agent_response = {
                            "role": "assistant",
                            "type": "text",
                            "content": result.get("message", result["output"])
                        }
                        conversation_objs.append(ChatMessage(agent_response))

                        # Update chat.last_updated
                        chat.last_updated = datetime.now(timezone.utc).isoformat()
                        db.commit()

                        # Return the plain text to the client
                        await websocket.send_text(agent_response["content"])

                    elif result["type"] == "based":
                        #
                        # 2) A brand-new Based file was generated
                        #    - Create a new ChatFile for it (if not existing)
                        #    - Create the first ChatFileVersion with 'output' as content
                        #    - Update chat.last_updated
                        #    - Return updated chat files to the frontend
                        #
                        based_filename = result.get("based_filename", "new_based_file.based")
                        file_content = result["output"]

                        # 2a) Create a new ChatFile record for the .based file
                        new_based_file_id = str(uuid.uuid4())
                        new_chat_file = ChatFile(
                            id=new_based_file_id,
                            filename=based_filename,
                            path="(in-memory)",  # or a real path if needed
                            chat_id=chat.id
                        )
                        db.add(new_chat_file)

                        # 2b) Create an initial ChatFileVersion
                        new_version_id = str(uuid.uuid4())
                        new_chat_file_version = ChatFileVersion(
                            id=new_version_id,
                            chat_file_id=new_based_file_id,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            content=file_content
                        )
                        db.add(new_chat_file_version)
                        
                        # Update chat.last_updated
                        chat.last_updated = datetime.now(timezone.utc).isoformat()
                        db.commit()

                        # 2c) Send a response to the frontend with the new file
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
                        #
                        # 3) We have a unified diff for an existing .based file
                        #    - Apply the diff to the existing latest content
                        #    - Create a new ChatFileVersion as the new "latest" version
                        #    - Update all older versions' diffs accordingly
                        #    - Update chat.last_updated
                        #    - Return updated chat files to the frontend
                        #
                        if not selected_based_file_obj:
                            await websocket.send_json({"error": "No selected .based file to apply diff."})
                            continue

                        diff_text = result["output"]
                        # 3a) Find the corresponding ChatFile record in DB
                        chat_file_id = selected_based_file_obj.file_id
                        existing_chat_file = db.query(ChatFile).filter(ChatFile.id == chat_file_id).first()
                        if not existing_chat_file:
                            await websocket.send_json({"error": f"ChatFile not found for id={chat_file_id}"})
                            continue

                        # 3b) Get the latest version content
                        latest_version_db = (
                            db.query(ChatFileVersion)
                            .filter(ChatFileVersion.chat_file_id == chat_file_id)
                            .order_by(ChatFileVersion.timestamp.desc())
                            .first()
                        )
                        if not latest_version_db:
                            await websocket.send_json({"error": "No existing version found for this .based file."})
                            continue
                        
                        old_content = latest_version_db.content
                        
                        # 3c) Apply diff locally
                        try:
                            import app.core.unifieddiff as ud
                            new_content = ud.apply_patch(old_content, diff_text)
                        except Exception as e:
                            await websocket.send_json({"error": f"Applying diff failed: {str(e)}"})
                            continue

                        # 3d) Create a new version with new content
                        new_version_id = str(uuid.uuid4())
                        new_version = ChatFileVersion(
                            id=new_version_id,
                            chat_file_id=chat_file_id,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            content=new_content
                        )
                        db.add(new_version)
                        
                        # 3e) Recompute diffs for older versions relative to this new version.
                        # We store them in memory so we can return them to the frontend, but we do
                        # NOT persist them to the DB (your schema has no column for storing these).
                        older_diffs = []
                        all_versions = (
                            db.query(ChatFileVersion)
                            .filter(ChatFileVersion.chat_file_id == chat_file_id)
                            .order_by(ChatFileVersion.timestamp)
                            .all()
                        )

                        for ver in all_versions:
                            if ver.id != new_version.id:
                                patch_diff = ud.make_patch(ver.content, new_version.content)
                                older_diffs.append({
                                    "version_id": ver.id,
                                    "diff": patch_diff
                                })

                        # 3f) Update chat.last_updated
                        chat.last_updated = datetime.now(timezone.utc).isoformat()
                        db.commit()

                        # 3g) Return an agent response
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
                                    "based_content": diff_text,
                                })
                            )
                        )
                        await websocket.send_json({"action": "agent_response", "message": agent_response})
                    else:
                        # Unknown type
                        await websocket.send_json({"error": "Unknown response type from agent."})
                elif action == "revert_version":
                    """
                    The frontend should send, at minimum:
                    {
                        "action": "revert_version",
                        "version_id": "...",
                        "filename": "...",  # The .based file name or ID
                    }
                    This endpoint will:
                    1. Look up the chosen ChatFileVersion by version_id.
                    2. Create a new ChatFileVersion with the same content, making it the new latest version.
                    3. Update chat.last_updated.
                    4. Return an 'agent_response' indicating success, along with the new version's content.
                    """
                    version_id = message_data.get("version_id")
                    filename = message_data.get("filename")
                    if not version_id or not filename:
                        await websocket.send_json({"error": "Missing version_id or filename for revert_version."})
                        continue

                    # 1) Find the older version record
                    old_version = db.query(ChatFileVersion).filter(ChatFileVersion.id == version_id).first()
                    if not old_version:
                        await websocket.send_json({"error": f"No version found for version_id={version_id}"})
                        continue
                    
                    # 2) Find the corresponding ChatFile by filename or ID (depending on your usage)
                    #    If you are using the .based file 'name' to identify it:
                    chat_file = db.query(ChatFile).filter(ChatFile.filename == filename).first()
                    #    Alternatively, if you have a 'file_id' from the client, filter by ChatFile.id == file_id
                    
                    if not chat_file:
                        await websocket.send_json({"error": f"No .based file found for filename={filename}"})
                        continue

                    # 3) Create a new ChatFileVersion referencing old_version.content
                    new_version_id = str(uuid.uuid4())
                    revert_version = ChatFileVersion(
                        id=new_version_id,
                        chat_file_id=chat_file.id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        content=old_version.content
                    )
                    db.add(revert_version)
                    
                    # 4) Update chat.last_updated
                    chat.last_updated = datetime.now(timezone.utc).isoformat()
                    db.commit()

                    # 5) Return updated .based file info to the frontend
                    agent_response = {
                        "role": "assistant",
                        "type": "file",
                        "content": {
                            "based_filename": chat_file.filename,
                            "based_content": old_version.content,
                            "message": f"Reverted to version {version_id}; new version is {new_version_id}"
                        }
                    }

                    # If you'd like to log this in the conversation, you can do so:
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

                else:
                    await websocket.send_json({"error": "Unknown action."})
            else:
                # Treat as a plain text chat message.
                user_message = ChatMessage(
                    role="user",
                    type="text",
                    content=raw_data
                )

                conversation_objs.append(user_message)

                response_text = f"Echo: {raw_data}"
                assistant_message = ChatMessage(
                    role="assistant",
                    type="text",
                    content=response_text
                )

                conversation_objs.append(assistant_message)
                await websocket.send_text(response_text)

    except WebSocketDisconnect:
        # 1) Save the conversation messages in `conversation_objs` to the DB
        #    (or just the newly added ones if you prefer a difference approach).

        for msg in conversation_objs:
            # If we've already stored this message in the DB, skip it.
            # Otherwise, create a new ChatConversation row.
            # You can track "already stored" with an attribute or a separate list for new messages only.
            
            # Example approach: if the message doesn't have a DB ID, it's new.
            # We'll do a naive approach here: store everything again that hasn't been stored,
            # but in practice you might keep track of them with a "new vs. existing" marker.
            
            # 2) Build a ChatConversation row
            new_chat_convo = ChatConversation(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=msg.role,
                type=msg.type,
                content=(
                    # if content is a dict or object, convert to JSON string
                    json.dumps(msg.content) if isinstance(msg.content, dict) else str(msg.content)
                )
            )
            db.add(new_chat_convo)

        # 3) Commit changes
        db.commit()

        # 4) (Optionally) close the DB session
        db.close()
        
        # 5) Close the websocket connection gracefully (optional in a Disconnect block)
        await websocket.close()