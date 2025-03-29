# app/routers/ws_initpayload.py
import os
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import PyPDF2

from app.schemas.ws import (
    WsInitialPayload,
    ChatMessage,
    ChatFileText,
    ChatFileBased,
    ChatFileBasedVersion,
    WorkspaceFile,
    ChatFileItem
)
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.models.chat_conversation import ChatConversation
from app.models.chat_file_version import ChatFileVersion
from app.models.file import File as FileModel
from app.models.model import Model as ModelModel
import app.core.unifieddiff as unifieddiff
from app.core.config import parse_file_content

def detect_file_type(filename: str) -> str:
    """
    Basic extension-based file type classification.
    Returns one of: 
      "code", "pdf", "csv", "markdown", "computer", "image", "based", or "other"
    """
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in ["py", "js", "ts", "java", "cpp", "c", "cs", "rb", "go", "rs"]:
        return "code"
    elif ext == "pdf":
        return "pdf"
    elif ext == "csv":
        return "csv"
    elif ext in ["md", "markdown"]:
        return "markdown"
    elif ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
        return "image"
    elif ext in ["exe", "bin", "dll"]:
        return "computer"
    elif ext == "based":
        return "based"
    else:
        return "other"


def build_initial_payload(db: Session, chat_id: str) -> dict:
    """
    Builds the initial data payload for a given chat_id:
      1. Loads the Chat record, conversation, files, etc.
      2. Returns a dict with:
         - "chat": The Chat model instance
         - "conversation_objs": in-memory ChatMessage list
         - "payload_json": final JSON (via model_dump) to send to the client

    If there's an error, returns {"error": "..."}.
    """
    # 1) Load the chat record
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return {"error": "Chat not found."}

    # 2) Convert DB conversation -> List[ChatMessage]
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

    print("=== Loading chat files... ===")
    print(conversation_objs)

    # 3) Load and partition chat files
    chat_files = db.query(ChatFile).filter(ChatFile.chat_id == chat.id).all()

    # 4) Create a single list of ChatFileItem
    chat_files_list = []

    for cfile in chat_files:
        # Step A: detect file type
        file_type = detect_file_type(cfile.filename)

        # Step B: parse textual content if needed
        file_content = ""
        if file_type in ["code", "pdf", "csv", "markdown"]:
            file_content = parse_file_content(cfile.path, file_type)
        elif file_type == "based":
            versions = (
                    db.query(ChatFileVersion)
                    .filter(ChatFileVersion.chat_file_id == cfile.id)
                    .order_by(ChatFileVersion.timestamp)
                    .all()
                )
            if versions:
                latest_version = versions[-1]
                file_content = latest_version.content
                

        # Step C: Build the file URL – e.g.:
        url = f"/uploads/files/{cfile.id}_{cfile.filename}" if not cfile.s3_url else cfile.s3_url

        # Step D: For code, guess a language from extension or store None
        # you can do that inline or have a detect_file_type_and_language
        language = None
        if file_type == "code":
            ext = cfile.filename.lower().rsplit(".", 1)[-1]
            if ext == "py":
                language = "python"
            # etc.

        # Step E: Build ChatFileItem
        new_item = {
            "id": cfile.id,
            "name": cfile.filename,
            "content": file_content,
            "language": language,
            "type": file_type,
            "url": url
        }
        chat_files_list.append(new_item)

    chat_files_based_objs = []

    for cfile in chat_files:
        ext = cfile.filename.lower().rsplit(".", 1)[-1]
        if ext == "based":
            # Load version history
            versions = (
                db.query(ChatFileVersion)
                .filter(ChatFileVersion.chat_file_id == cfile.id)
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

            cfile_based = ChatFileBased(
                file_id=cfile.id,
                name=cfile.filename,
                latest_content=latest_content,
                versions=version_objs,
                type="based"
            )
            chat_files_based_objs.append(cfile_based)

    print("\n\n\n\n\n\n\n\n")
    print("======== chat_files_list ========")
    print(chat_files_list)
    print("\n\n\n\n\n\n\n\n")

    # 5) Load model names
    models_query = db.query(ModelModel).filter(ModelModel.user_id == chat.user_id).all()
    model_names = [m.name for m in models_query]

    # 6) Build a WsInitialPayload object
    payload_obj = WsInitialPayload(
        chat_id=str(chat.id),
        chat_name=chat.name,
        conversation=conversation_objs,
        chat_files=chat_files_list,
        workspace_id=str(chat.workspace_id),
        chat_files_based=chat_files_based_objs,
        models=model_names,
        initial=True
    )

    # 7) Create final JSON via model_dump
    data_to_send = payload_obj.model_dump()

    return {
        "chat": chat,  # So the router can keep a reference if needed
        "conversation_objs": conversation_objs,
        "payload_json": data_to_send
    }
