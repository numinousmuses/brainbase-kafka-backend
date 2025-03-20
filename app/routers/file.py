# app/routers/file.py
import os
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.file import File as FileModel  # Workspace file model
from app.models.chat import Chat
from app.models.chat_file import ChatFile
from app.schemas.file import FileUploadResponse

router = APIRouter()

# Define the directory where uploaded files will be stored.
UPLOAD_DIRECTORY = "uploads/files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    user_id: str = Form(...),
    target_id: str = Form(...),
    is_chat: bool = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload files to either a workspace or a chat.
    
    Parameters:
      - **user_id:** The ID of the user uploading the file.
      - **target_id:** If uploading to a workspace, this is the workspace ID.
                      If uploading to a chat, this is the chat ID.
      - **is_chat:** Boolean flag. If true, the file is added to both the chat and its workspace.
      - **files:** List of file uploads.
    
    Processing:
      - Saves each file once on disk.
      - If **is_chat** is false:
          - Creates a record in the File table (linked to the workspace).
      - If **is_chat** is true:
          - Looks up the Chat (to retrieve its workspace ID).
          - Creates a record in the ChatFile table (for the chat) 
            and in the File table (for the workspace) using the same file ID.
    
    Returns:
      - A list of file IDs for the uploaded files.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    
    uploaded_file_ids = []
    
    if is_chat:
        # Look up the chat record.
        chat = db.query(Chat).filter(Chat.id == target_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found.")
        # Retrieve the workspace ID from the chat.
        workspace_id = chat.workspace_id
        
        for upload in files:
            file_id = str(uuid4())
            unique_filename = f"{file_id}_{upload.filename}"
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
            
            # Save the file on disk.
            with open(file_path, "wb") as buffer:
                buffer.write(await upload.read())
            
            # Create a record in the File table for the workspace.
            new_file = FileModel(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                workspace_id=workspace_id
            )
            db.add(new_file)
            
            # Create a record in the ChatFile table for the chat.
            new_chat_file = ChatFile(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                chat_id=chat.id
            )
            db.add(new_chat_file)
            
            uploaded_file_ids.append(file_id)
    
    else:
        # Uploading directly to a workspace.
        from app.models.workspace import Workspace
        workspace = db.query(Workspace).filter(Workspace.id == target_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")
        
        for upload in files:
            file_id = str(uuid4())
            unique_filename = f"{file_id}_{upload.filename}"
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await upload.read())
            
            new_file = FileModel(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                workspace_id=workspace.id
            )
            db.add(new_file)
            
            uploaded_file_ids.append(file_id)
    
    db.commit()
    return FileUploadResponse(files=uploaded_file_ids)