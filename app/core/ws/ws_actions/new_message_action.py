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
    print("=== Entering handle_new_message_action ===")
    print("Incoming message_data:", message_data)
    
    model_name = message_data.get("model", "default_model")
    prompt = message_data.get("prompt", "")
    is_first_prompt = message_data.get("is_first_prompt", False)
    is_chat_or_composer = message_data.get("is_chat_or_composer", False)
    selected_filename = message_data.get("selected_filename", None)
    
    print("Parsed message_data:")
    print(" - model_name:", model_name)
    print(" - prompt:", prompt)
    print(" - is_first_prompt:", is_first_prompt)
    print(" - is_chat_or_composer:", is_chat_or_composer)
    print(" - selected_filename:", selected_filename)

    # Add the user message to conversation
    user_message = ChatMessage(
        role="user",
        type="text",
        content=prompt
    )
    conversation_objs.append(user_message)
    print("Appended user message to conversation_objs:", user_message)

    # Find the model
    print("Querying model in DB with name:", model_name)
    model_obj = db.query(ModelModel).filter(ModelModel.name == model_name).first()
    print("Found model_obj:", model_obj)
    if not model_obj:
        error_msg = {"error": "Model not found."}
        print("Error:", error_msg)
        await websocket.send_json(error_msg)
        return

    model_ak = model_obj.ak
    model_base_url = model_obj.base_url
    print("Model credentials:")
    print(" - model_ak:", model_ak)
    print(" - model_base_url:", model_base_url)

    # Identify the selected .based file, if any, and the "other" based files
    selected_based_file_obj = None
    other_based_files_dict = []
    print("Processing chat_files_based_objs, selected_filename:", selected_filename)
    for bf_obj in chat_files_based_objs:
        print(" - Inspecting based file:", bf_obj.name)
        if selected_filename and bf_obj.name == selected_filename:
            selected_based_file_obj = bf_obj
            print("   -> Selected based file found:", bf_obj.name)
        else:
            other_based_files_dict.append(bf_obj.dict())
            print("   -> Adding to other_based_files_dict:", bf_obj.name)

    # If no file was explicitly selected, treat all as 'other'
    if not selected_based_file_obj:
        print("No selected based file found. Using all based files as other_based_files_dict.")
        other_based_files_dict = [bf_obj.dict() for bf_obj in chat_files_based_objs]

    selected_based_file_dict = selected_based_file_obj.dict() if selected_based_file_obj else None
    print("Final selected_based_file_dict:", selected_based_file_dict)
    print("Other based files dict:", other_based_files_dict)

    # 1) Call handle_new_message
    print("Calling handle_new_message with parameters:")
    print({
        "model_name": model_name,
        "model_ak": model_ak,
        "model_base_url": model_base_url,
        "selected_filename": selected_filename,
        "selected_based_file_dict": selected_based_file_dict,
        "prompt": prompt,
        "is_first_prompt": is_first_prompt,
        "is_chat_or_composer": is_chat_or_composer,
        "conversation": [cm.dict() for cm in conversation_objs],
        "chat_files_text": [cft.dict() for cft in chat_files_text_objs],
        "other_based_files": other_based_files_dict
    })
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
    print("Result from handle_new_message:", result)

    # 2) Process agent result
    if result["type"] == "response":
        print("Processing 'response' type result")
        # Plain text response from agent
        agent_response = {
            "role": "assistant",
            "type": "text",
            "content": result.get("message", result["output"])
        }
        print("Agent response constructed:", agent_response)
        conversation_objs.append(ChatMessage(**agent_response))
        print("Appended agent response to conversation_objs.")

        # Update chat.last_updated
        chat.last_updated = datetime.now(timezone.utc).isoformat()
        print("Updated chat.last_updated to:", chat.last_updated)
        db.commit()
        print("DB commit successful.")

        # Return text to client
        print("Sending text response to websocket:", agent_response["content"])
        await websocket.send_text(agent_response["content"])

    elif result["type"] == "based":
        print("Processing 'based' type result")
        # A brand-new .based file was created
        based_filename = result.get("based_filename", "new_based_file.based")
        file_content = result["output"]
        print("New based file details:")
        print(" - based_filename:", based_filename)
        print(" - file_content:", file_content)

        new_based_file_id = str(uuid.uuid4())
        print("Generated new_based_file_id:", new_based_file_id)
        new_chat_file = ChatFile(
            id=new_based_file_id,
            filename=based_filename,
            path="(in-memory)",
            chat_id=chat.id
        )
        db.add(new_chat_file)
        print("Added new_chat_file to DB:", new_chat_file)

        new_version_id = str(uuid.uuid4())
        print("Generated new_version_id:", new_version_id)
        new_chat_file_version = ChatFileVersion(
            id=new_version_id,
            chat_file_id=new_based_file_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=file_content
        )
        db.add(new_chat_file_version)
        print("Added new_chat_file_version to DB:", new_chat_file_version)

        chat.last_updated = datetime.now(timezone.utc).isoformat()
        print("Updated chat.last_updated to:", chat.last_updated)
        db.commit()
        print("DB commit successful.")

        agent_response = {
            "role": "assistant",
            "type": "file",
            "content": {
                "based_filename": based_filename,
                "based_content": file_content
            }
        }
        print("Constructed agent_response for 'based' type:", agent_response)

        new_convo_block = ChatMessage(
            role="assistant",
            type="file",
            content=json.dumps({
                "based_filename": based_filename,
                "based_content": file_content
            })
        )
        conversation_objs.append(new_convo_block)
        print("Appended new conversation block for based file:", new_convo_block)
        await websocket.send_json({"action": "agent_response", "message": agent_response, "block": new_convo_block})
        print("Sent JSON response for 'based' type over websocket.")

    elif result["type"] == "diff":
        print("Processing 'diff' type result")
        # We have a diff for an existing .based file
        if not selected_based_file_obj:
            error_msg = {"error": "No selected .based file to apply diff."}
            print("Error:", error_msg)
            await websocket.send_json(error_msg)
            return

        diff_text = result["output"]
        print("Diff text received:", diff_text)
        chat_file_id = selected_based_file_obj.file_id
        print("Using chat_file_id:", chat_file_id)
        existing_chat_file = db.query(ChatFile).filter(ChatFile.id == chat_file_id).first()
        print("Existing chat file:", existing_chat_file)
        if not existing_chat_file:
            error_msg = {"error": f"ChatFile not found for id={chat_file_id}"}
            print("Error:", error_msg)
            await websocket.send_json(error_msg)
            return

        latest_version_db = (
            db.query(ChatFileVersion)
            .filter(ChatFileVersion.chat_file_id == chat_file_id)
            .order_by(ChatFileVersion.timestamp.desc())
            .first()
        )
        print("Latest version from DB:", latest_version_db)
        if not latest_version_db:
            error_msg = {"error": "No existing version found for this .based file."}
            print("Error:", error_msg)
            await websocket.send_json(error_msg)
            return

        old_content = latest_version_db.content
        print("Old content from latest version:", old_content)

        # Apply the diff
        try:
            new_content = unifieddiff.apply_patch(old_content, diff_text)
            print("New content after applying diff:", new_content)
        except Exception as e:
            error_msg = {"error": f"Applying diff failed: {str(e)}"}
            print("Error during diff application:", error_msg)
            await websocket.send_json(error_msg)
            return

        # Create a new version
        new_version_id = str(uuid.uuid4())
        print("Generated new_version_id for diff:", new_version_id)
        new_version = ChatFileVersion(
            id=new_version_id,
            chat_file_id=chat_file_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=new_content
        )
        db.add(new_version)
        print("Added new version to DB:", new_version)

        # Optionally recompute older diffs (not always needed, but included here)
        older_diffs = []
        all_versions = (
            db.query(ChatFileVersion)
            .filter(ChatFileVersion.chat_file_id == chat_file_id)
            .order_by(ChatFileVersion.timestamp)
            .all()
        )
        print("All versions for recompute diffs:", all_versions)
        for ver in all_versions:
            if ver.id != new_version.id:
                patch_diff = unifieddiff.make_patch(ver.content, new_version.content)
                older_diffs.append({
                    "version_id": ver.id,
                    "diff": patch_diff
                })
                print("Computed diff for version", ver.id, ":", patch_diff)

        # Update chat.last_updated
        chat.last_updated = datetime.now(timezone.utc).isoformat()
        print("Updated chat.last_updated to:", chat.last_updated)
        db.commit()
        print("DB commit successful after diff update.")

        agent_response = {
            "role": "assistant",
            "type": "file",
            "content": {
                "based_filename": selected_based_file_obj.name,
                "based_content": new_content
            }
        }
        print("Constructed agent_response for diff type:", agent_response)

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
        print("Appended conversation block with diff details.")
        await websocket.send_json({"action": "agent_response", "message": agent_response})
        print("Sent JSON response for 'diff' type over websocket.")

    else:
        error_msg = {"error": "Unknown response type from agent."}
        print("Error: Unknown response type from agent. Sending error message:", error_msg)
        await websocket.send_json(error_msg)
    
    print("=== Exiting handle_new_message_action ===")
