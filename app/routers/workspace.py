# app/routers/workspace.py
import os
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.workspace import Workspace
from app.models.file import File as FileModel  # Alias to avoid conflict with Python's built-in `file`
from app.schemas.workspace import WorkspaceNewResponse, FileResponse, WorkspaceRenameResponse

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

@router.patch("/rename", response_model=WorkspaceRenameResponse)
def rename_workspace(
    workspace_id: str = Form(...),
    new_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Rename an existing workspace.
    
    - **workspace_id**: The ID of the workspace to rename.
    - **new_name**: The new name for the workspace.
    
    All related data remains unchanged.
    
    Returns:
      - **workspace_id**: The workspace's ID.
      - **new_name**: The updated workspace name.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
         raise HTTPException(status_code=404, detail="Workspace not found.")
    
    workspace.name = new_name
    db.commit()
    db.refresh(workspace)
    
    return WorkspaceRenameResponse(workspace_id=workspace.id, new_name=workspace.name)

@router.delete("/delete/{workspace_id}")
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)):
    """
    Delete a workspace and all associated data (chats, files, etc.).
    
    - **workspace_id**: The ID of the workspace to delete.
    
    This endpoint performs the following:
      - Deletes all physical files on disk associated with the workspace.
      - Deletes the workspace record, which cascades deletion of all related chats and file records.
    
    Returns a confirmation message.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
         raise HTTPException(status_code=404, detail="Workspace not found.")
    
    # Delete all physical files associated with the workspace.
    for file in workspace.files:
         if os.path.exists(file.path):
             os.remove(file.path)
    
    # Delete the workspace record (cascade deletion will remove chats and files).
    db.delete(workspace)
    db.commit()
    
    return {"detail": "Workspace and all associated data deleted successfully."}
