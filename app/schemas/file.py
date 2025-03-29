# app/schemas/file.py
from pydantic import BaseModel
from typing import List, Optional

class FileRenameResponse(BaseModel):
    file_id: str
    new_filename: str
    new_path: str

class UploadedFileInfo(BaseModel):
    id: str
    name: str
    content: Optional[str]
    language: Optional[str]
    type: str
    url: str

class FileUploadResponse(BaseModel):
    files: List[UploadedFileInfo]  # Each file's metadata