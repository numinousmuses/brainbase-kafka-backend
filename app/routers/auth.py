# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.model import Model  # Ensure this is imported
from app.schemas.auth import AuthRequest, AuthResponse, WorkspaceResponse, WorkspaceChat, WorkspaceFile, ModelResponse

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
def auth(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Receives an email, checks if the user exists.
    If not, creates the user (and a default workspace).
    Returns the user's info along with all their workspaces,
    including file and chat summaries for each workspace, and the user's models.
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
        # Build list of files for this workspace
        file_list = []
        for file in workspace.files:
            file_list.append(WorkspaceFile(
                id=file.id,
                filename=file.filename
            ))

        # Build list of chats for this workspace
        chat_list = []
        for chat in workspace.chats:
            chat_list.append(WorkspaceChat(
                id=chat.id,
                name=chat.name,
                last_updated=chat.last_updated
            ))
        
        workspace_responses.append(
            WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                files=file_list,
                chats=chat_list
            )
        )

    # 4. Retrieve user's models and convert to ModelResponse list.
    models_query = db.query(Model).filter(Model.user_id == user.id).all()
    model_responses = [
        ModelResponse(
            id=model.id,
            name=model.name,
            base_url=model.base_url,
            user_id=model.user_id
        )
        for model in models_query
    ]

    # 5. Return AuthResponse with user info, workspaces, and models.
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        workspaces=workspace_responses,
        models=model_responses
    )
