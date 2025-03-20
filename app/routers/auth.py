# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auth import AuthRequest, AuthResponse, WorkspaceResponse

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
def auth(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Receives an email, checks if the user exists.
    If not, creates the user (and a default workspace).
    Returns the user's info along with all their workspaces.
    """

    # 1. Check if the user exists
    user = db.query(User).filter(User.email == payload.email).first()

    # 2. If not found, create user and default workspace
    if not user:
        user = User(id=str(uuid4()), email=payload.email)
        db.add(user)

        # Create a default workspace for new users
        default_workspace = Workspace(
            id=str(uuid4()), 
            name="Default Workspace",
            owner_id=user.id
        )
        db.add(default_workspace)

        db.commit()
        db.refresh(user)
        db.refresh(default_workspace)

    # 3. Retrieve the user’s workspaces
    workspaces = db.query(Workspace).filter(Workspace.owner_id == user.id).all()

    # 4. Return AuthResponse with user and workspace details
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        workspaces=[
            WorkspaceResponse(id=w.id, name=w.name)
            for w in workspaces
        ]
    )
