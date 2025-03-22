# /schemas/ws.py
from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    role: str
    type: str  # e.g., "text", "file"
    content: str

class ChatFileText(BaseModel):
    file_id: str
    name: str
    content: str  # For text files, this is the extracted text; for images, this can be a URL/path.
    type: str     # Expected "text" or "image"

class ChatFileBasedVersion(BaseModel):
    version_id: str
    timestamp: str
    diff: str

class ChatFileBased(BaseModel):
    file_id: str
    name: str
    latest_content: str
    versions: List[ChatFileBasedVersion]
    type: str  # Should be "based"

class WorkspaceFile(BaseModel):
    file_id: str
    name: str

class WsInitialPayload(BaseModel):
    chat_id: str
    chat_name: str
    conversation: List[ChatMessage]
    chat_files_text: List[ChatFileText]
    chat_files_based: List[ChatFileBased]
    workspace_files: List[WorkspaceFile]
    workspace_id: str
    models: List[str]
    initial: bool
