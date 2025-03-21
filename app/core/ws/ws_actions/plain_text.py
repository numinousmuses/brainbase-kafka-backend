from fastapi import WebSocket
from schemas.ws import ChatMessage


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
