import json
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.schemas.ws import ChatMessage
from app.models.chat import Chat

# Import our sub-handlers from within the same package
from .plain_text import handle_plain_text
from .upload_file import handle_upload_file
from .new_message_action import handle_new_message_action
from .revert_version import handle_revert_version
from .delete_file import handle_delete_file


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
    elif action == "delete_file":
        await handle_delete_file(db, websocket, message_data, conversation_objs, chat)
    else:
        await websocket.send_json({"error": f"Unknown action: {action}"})
