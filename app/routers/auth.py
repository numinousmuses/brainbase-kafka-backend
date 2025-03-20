# app/routers/auth.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from uuid import uuid4

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr

class LoginResponse(BaseModel):
    uuid: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # In a real application, check if the user exists in your database.
    # If not, create a new user entry.
    user_uuid = str(uuid4())
    # For now, return the generated UUID.
    return LoginResponse(uuid=user_uuid)
