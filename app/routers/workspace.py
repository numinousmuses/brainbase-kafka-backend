# app/routers/workspace.py
import os
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.workspace import Workspace
from app.models.file import File as FileModel  # Alias to avoid conflict with Python's built-in `file`
from app.schemas.workspace import WorkspaceNewResponse, FileResponse

router = APIRouter()

# Define the upload directory for workspace files
UPLOAD_DIRECTORY = "uploads/files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

@router.post("/new", response_model=WorkspaceNewResponse)
async def create_workspace(
    owner_id: str = Form(...),
    name: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a new workspace with the given name and optional file uploads.
    
    - **owner_id** and **name** are received as form fields.
    - **files** are attached as file uploads.
    - A new UUID is generated for the workspace.
    - Each uploaded file is saved to disk in the UPLOAD_DIRECTORY.
    - File metadata (original filename, generated file_id, and path) is stored in the database.
    
    Returns:
        - workspace_id: The generated UUID for the workspace.
        - files: A list of objects containing the file_id and original filename.
    """
    # Generate a new UUID for the workspace
    workspace_id = str(uuid4())
    new_workspace = Workspace(id=workspace_id, name=name, owner_id=owner_id)
    db.add(new_workspace)

    file_responses = []
    if files:
        for upload in files:
            file_id = str(uuid4())
            # Create a unique filename using the file_id
            unique_filename = f"{file_id}_{upload.filename}"
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
            # Save the file contents to disk
            with open(file_path, "wb") as buffer:
                buffer.write(await upload.read())
            # Create a database record for the file
            new_file = FileModel(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                workspace_id=workspace_id
            )
            db.add(new_file)
            file_responses.append(FileResponse(file_id=file_id, filename=upload.filename))
    
    db.commit()
    
    return WorkspaceNewResponse(
        workspace_id=workspace_id,
        files=file_responses
    )
