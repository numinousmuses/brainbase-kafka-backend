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
    WorkspaceFile
)
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.models.chat_conversation import ChatConversation
from app.models.chat_file_version import ChatFileVersion
from app.models.file import File as FileModel
from app.models.model import Model as ModelModel
import app.core.unifieddiff as unifieddiff


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

    # 3) Load and partition chat files
    chat_files = db.query(ChatFile).filter(ChatFile.chat_id == chat.id).all()

    # We'll parse .txt/.pdf files to store their text, if needed
    parsed_files = {}
    for cfile in chat_files:
        fname = cfile.filename.lower()
        if fname.endswith(".txt"):
            try:
                with open(cfile.path, "r", encoding="utf-8") as f:
                    parsed_text = f.read()
            except Exception:
                parsed_text = ""
            parsed_files[cfile.id] = parsed_text
        elif fname.endswith(".pdf"):
            try:
                with open(cfile.path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    parsed_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            parsed_text += text
            except Exception:
                parsed_text = "[Error parsing PDF]"
            parsed_files[cfile.id] = parsed_text

    chat_files_text_objs = []
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
        else:
            # non-based file
            if ext in ["jpg", "jpeg", "png", "gif"]:
                file_type = "image"
                content = cfile.path  # image path
            else:
                file_type = "text"
                content = parsed_files.get(cfile.id, "")

            cfile_text = ChatFileText(
                file_id=cfile.id,
                name=cfile.filename,
                content=content,
                type=file_type
            )
            chat_files_text_objs.append(cfile_text)

    # 4) Load workspace files not attached to this chat & not .based
    workspace_files_all = db.query(FileModel).filter(FileModel.workspace_id == chat.workspace_id).all()
    chat_file_ids = {cf.id for cf in chat_files}
    workspace_files_objs = []
    for wf in workspace_files_all:
        if wf.id not in chat_file_ids and not wf.filename.lower().endswith(".based"):
            workspace_files_objs.append(
                WorkspaceFile(
                    file_id=wf.id,
                    name=wf.filename
                )
            )

    # 5) Load model names
    models_query = db.query(ModelModel).filter(ModelModel.user_id == chat.user_id).all()
    model_names = [m.name for m in models_query]

    # 6) Build a WsInitialPayload object
    payload_obj = WsInitialPayload(
        chat_id=str(chat.id),
        chat_name=chat.name,
        conversation=conversation_objs,
        chat_files_text=chat_files_text_objs,
        chat_files_based=chat_files_based_objs,
        workspace_files=workspace_files_objs,
        workspace_id=str(chat.workspace_id),
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
