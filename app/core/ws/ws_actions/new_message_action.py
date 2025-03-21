import json
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.schemas.ws import ChatMessage
from app.models.model import Model as ModelModel
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.models.chat_file_version import ChatFileVersion
import app.core.unifieddiff as unifieddiff

from app.core.basedagent import handle_new_message


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

        # Optionally recompute older diffs (not always needed, but included here)
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