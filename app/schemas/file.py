# app/schemas/file.py
from pydantic import BaseModel
from typing import List

class FileUploadResponse(BaseModel):
    files: List[str]

class FileRenameResponse(BaseModel):
    file_id: str
    new_filename: str
    new_path: str
