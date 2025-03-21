# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class WorkspaceFile(BaseModel):
    id: str
    filename: str

class WorkspaceChat(BaseModel):
    id: str
    name: str
    last_updated: Optional[str] = None

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    files: List[WorkspaceFile] = []
    chats: List[WorkspaceChat] = []

class AuthRequest(BaseModel):
    email: EmailStr

class AuthResponse(BaseModel):
    user_id: str
    email: EmailStr
    workspaces: List[WorkspaceResponse]
