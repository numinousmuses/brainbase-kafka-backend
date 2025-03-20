# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auth import AuthRequest, AuthResponse, WorkspaceResponse, WorkspaceChat

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
def auth(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Receives an email, checks if the user exists.
    If not, creates the user (and a default workspace).
    Returns the user's info along with all their workspaces,
    including chat summaries for each workspace.
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

    # 3. Retrieve the user's workspaces
    workspaces = db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    workspace_responses = []

    for workspace in workspaces:
        chat_summaries = []
        # Use the relationship from Workspace to Chat
        for chat in workspace.chats:
            # Compute the total number of versions for .based files in this chat
            num_versions = sum(len(chat_file.versions) for chat_file in chat.chat_files)
            chat_summary = WorkspaceChat(
                id=chat.id,
                name=chat.name,
                last_updated=chat.last_updated,
                num_versions=num_versions
            )
            chat_summaries.append(chat_summary)
        
        workspace_responses.append(
            WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                chats=chat_summaries
            )
        )

    # 4. Return AuthResponse with user info and workspace details
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        workspaces=workspace_responses
    )
