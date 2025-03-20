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
from app.schemas.file import FileUploadResponse, FileRenameResponse

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


@router.delete("/delete/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    """
    Delete a file by its file_id.
    
    This endpoint:
      - Removes the file from disk.
      - Deletes the record from the File table.
      - If a corresponding record exists in the ChatFile table, deletes that record as well.
    
    Returns a confirmation message.
    """
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_record:
         raise HTTPException(status_code=404, detail="File not found.")
    file_path = file_record.path
    # Remove file from disk if it exists.
    if os.path.exists(file_path):
         os.remove(file_path)
    # Delete file record from FileModel.
    db.delete(file_record)
    
    # Also, if a corresponding record exists in ChatFile, delete it.
    chat_file_record = db.query(ChatFile).filter(ChatFile.id == file_id).first()
    if chat_file_record:
         db.delete(chat_file_record)
    
    db.commit()
    return {"detail": "File deleted successfully."}


@router.patch("/rename", response_model=FileRenameResponse)
def rename_file(
    file_id: str = Form(...),
    new_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Rename a file identified by file_id.
    
    - Updates the filename in the File and ChatFile records.
    - Renames the file on disk. The new file path is constructed as: <file_id>_<new_name>
    
    Returns:
      - **file_id:** The file's ID.
      - **new_filename:** The new file name.
      - **new_path:** The new file path.
    """
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_record:
         raise HTTPException(status_code=404, detail="File not found.")
    
    old_path = file_record.path
    # Construct new filename and new path.
    new_filename = new_name  # We'll store only the new name without the file_id prefix in the record.
    new_unique_filename = f"{file_id}_{new_name}"
    new_path = os.path.join(UPLOAD_DIRECTORY, new_unique_filename)
    
    # Rename the file on disk if it exists.
    if os.path.exists(old_path):
         os.rename(old_path, new_path)
    
    # Update FileModel record.
    file_record.filename = new_name
    file_record.path = new_path
    db.add(file_record)
    
    # Update ChatFile record if exists.
    chat_file_record = db.query(ChatFile).filter(ChatFile.id == file_id).first()
    if chat_file_record:
         chat_file_record.filename = new_name
         chat_file_record.path = new_path
         db.add(chat_file_record)
    
    db.commit()
    return FileRenameResponse(
        file_id=file_id,
        new_filename=new_name,
        new_path=new_path
    )
