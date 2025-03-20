# app/schemas/workspace.py
from pydantic import BaseModel
from typing import List

class FileResponse(BaseModel):
    file_id: str
    filename: str

class WorkspaceNewResponse(BaseModel):
    workspace_id: str
    files: List[FileResponse] = []
