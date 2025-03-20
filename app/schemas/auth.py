# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import List

class AuthRequest(BaseModel):
    email: EmailStr

class WorkspaceResponse(BaseModel):
    id: str
    name: str

class AuthResponse(BaseModel):
    user_id: str
    email: EmailStr
    workspaces: List[WorkspaceResponse]
