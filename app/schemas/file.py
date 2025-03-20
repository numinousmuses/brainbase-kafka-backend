# app/schemas/file.py
from pydantic import BaseModel
from typing import List

class FileUploadResponse(BaseModel):
    files: List[str]