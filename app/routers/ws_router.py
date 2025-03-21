# app/routers/ws_router.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db

# Our splitted modules
from app.core.ws.ws_initpayload import build_initial_payload
from app.core.ws.ws_actions import handle_action
from app.core.ws.ws_disconnect import persist_on_disconnect

router = APIRouter()

@router.websocket("/ws/{chat_id}")
async def chat_ws(websocket: WebSocket, chat_id: str):
    """
    Main WebSocket handler that:
      1) Loads the chat + conversation in memory (via build_initial_payload).
      2) Sends the initial data to the client.
      3) Handles incoming actions in a loop.
      4) On disconnect, persists any unsaved conversation to DB.
    """
    await websocket.accept()
    
    db: Session = next(get_db())

    # 1) Build the initial payload (this loads the chat, conversation, chat files, etc. into memory)
    initial_data = build_initial_payload(db, chat_id)
    if isinstance(initial_data, dict) and "error" in initial_data:
        # If we got an error from build_initial_payload, let the client know and close
        await websocket.send_json(initial_data)
        await websocket.close()
        return

    # 2) Send the initial payload JSON to the client
    await websocket.send_json(initial_data["payload_json"])

    # 3) Keep references in memory for the entire session
    chat = initial_data["chat"]  # The Chat SQLAlchemy object
    conversation_objs = initial_data["conversation_objs"]  # In-memory list of ChatMessage
    # If build_initial_payload returns them, also store these:
    chat_files_based_objs = initial_data.get("chat_files_based_objs", [])
    chat_files_text_objs = initial_data.get("chat_files_text_objs", [])

    try:
        while True:
            # 4) Receive text from the WebSocket
            raw_data = await websocket.receive_text()

            # 5) Delegate to the handle_action function
            #    We pass in the references, so handle_action can read/modify them
            await handle_action(
                db=db,
                websocket=websocket,
                raw_data=raw_data,
                conversation_objs=conversation_objs,
                chat=chat,
                chat_files_based_objs=chat_files_based_objs,
                chat_files_text_objs=chat_files_text_objs
            )

    except WebSocketDisconnect:
        # 6) On disconnect, persist any conversation changes to the DB (and close the socket)
        await persist_on_disconnect(
            db=db,
            chat_id=chat_id,
            conversation_objs=conversation_objs,
            websocket=websocket
        )
