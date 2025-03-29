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
from app.schemas.file import FileUploadResponse, FileRenameResponse, UploadedFileInfo
import PyPDF2


router = APIRouter()

# Define the directory where uploaded files will be stored.
UPLOAD_DIRECTORY = "uploads/files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

def detect_file_type_and_language(filename: str, content: bytes):
    """
    Simple helper to guess file type and language from filename and/or content.
    Extend this logic as needed for your own use cases.
    """
    ext = os.path.splitext(filename)[1].lower()

    # Default type & language
    file_type = "other"
    language = None  # e.g., only set if type == "code"

    # Basic rules by extension
    if ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs"]:
        file_type = "code"
        # A quick guess at language based on extension
        if ext == ".py":
            language = "python"
        elif ext in [".js", ".ts"]:
            language = "javascript/typescript"
        elif ext == ".java":
            language = "java"
        elif ext in [".cpp", ".c"]:
            language = "c/cpp"
        elif ext == ".cs":
            language = "csharp"
        elif ext == ".rb":
            language = "ruby"
        elif ext == ".go":
            language = "go"
        elif ext == ".rs":
            language = "rust"

    elif ext == ".pdf":
        file_type = "pdf"
    elif ext == ".csv":
        file_type = "csv"
    elif ext in [".md", ".markdown"]:
        file_type = "markdown"
    elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        file_type = "image"
    elif ext in [".exe", ".bin", ".dll"]:
        file_type = "computer"

    return file_type, language


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    target_id: str = Form(...),
    is_chat: bool = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    s3_urls: Optional[List[str]] = Form(None),
):
    """
    Upload files to either a workspace or a chat.
    ...
    Returns:
      A list of file metadata objects with:
         - id
         - name
         - content
         - language
         - type
         - url
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    uploaded_files_info = []

    # --------------------
    # 1) If we're uploading to a Chat
    # --------------------
    if is_chat:
        print("Uploading to chat...")
        chat = db.query(Chat).filter(Chat.id == target_id).first()
        print("Chat:", chat)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found.")
        workspace_id = chat.workspace_id

        for upload in files:
            file_id = str(uuid4())
            unique_filename = f"{file_id}_{upload.filename}"
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

            # Read the file contents (for small files; handle large files carefully)
            file_bytes = await upload.read()

            # Save to disk
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)

            # Create DB records
            new_file = FileModel(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                workspace_id=workspace_id,
                s3_url=s3_urls[files.index(upload)]
            )
            db.add(new_file)

            new_chat_file = ChatFile(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                chat_id=chat.id,
                s3_url=s3_urls[files.index(upload)]
            )
            db.add(new_chat_file)

            # Infer type/language
            file_type, language = detect_file_type_and_language(upload.filename, file_bytes)

            # For textual code-like files, decode content
            # If you want to limit content size, you could slice or store partial
            decoded_content = None
            if file_type in ["code", "csv", "markdown"]:
                try:
                    decoded_content = file_bytes.decode("utf-8", errors="replace")
                except:
                    decoded_content = None
            elif file_type == "pdf":
                print("\n\n\n\n\n\n\n\n")
                print("Parsing PDF...")
                print("\n\n\n\n\n\n\n\n")
                try:
                    from io import BytesIO
                    pdf_stream = BytesIO(file_bytes)
                    reader = PyPDF2.PdfReader(pdf_stream)
                    pdf_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            pdf_text += text
                    decoded_content = pdf_text
                    print("\n\n\n\n\n\n\n\n")
                    print("PDF TEXT")
                    print(decoded_content)
                    print("\n\n\n\n\n\n\n\n")
                except Exception:
                    decoded_content = "[Error parsing PDF]"

            # Build the file info object
            file_info = UploadedFileInfo(
                id=file_id,
                name=upload.filename,
                content=decoded_content,
                language=language,
                type=file_type,
                url=s3_urls[files.index(upload)]
            )
            uploaded_files_info.append(file_info)

    # --------------------
    # 2) If we're uploading directly to a Workspace
    # --------------------
    else:
        from app.models.workspace import Workspace
        workspace = db.query(Workspace).filter(Workspace.id == target_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        for upload in files:
            file_id = str(uuid4())
            unique_filename = f"{file_id}_{upload.filename}"
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

            # Read the file contents
            file_bytes = await upload.read()

            # Save to disk
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)

            # Create a FileModel record
            new_file = FileModel(
                id=file_id,
                filename=upload.filename,
                path=file_path,
                workspace_id=workspace.id,
                s3_url=s3_urls[files.index(upload)]
            )
            db.add(new_file)

            # Infer type/language
            file_type, language = detect_file_type_and_language(upload.filename, file_bytes)

            # Decode content if it's something textual
            decoded_content = None
            if file_type in ["code", "csv", "markdown"]:
                try:
                    decoded_content = file_bytes.decode("utf-8", errors="replace")
                except:
                    decoded_content = None
            elif file_type == "pdf":
                print("\n\n\n\n\n\n\n\n")
                print("Parsing PDF...")
                print("\n\n\n\n\n\n\n\n")
                try:
                    from io import BytesIO
                    pdf_stream = BytesIO(file_bytes)
                    reader = PyPDF2.PdfReader(pdf_stream)
                    pdf_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            pdf_text += text
                    decoded_content = pdf_text
                    print("\n\n\n\n\n\n\n\n")
                    print("PDF TEXT")
                    print(decoded_content)
                    print("\n\n\n\n\n\n\n\n")
                except Exception:
                    decoded_content = "[Error parsing PDF]"

            # Build the file info object
            file_info = UploadedFileInfo(
                id=file_id,
                name=upload.filename,
                content=decoded_content,
                language=language,
                type=file_type,
                url=f"/{UPLOAD_DIRECTORY}/{unique_filename}"
            )
            uploaded_files_info.append(file_info)

    # Commit DB changes
    db.commit()

    # Return all file objects in a single response
    return FileUploadResponse(files=uploaded_files_info)

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
