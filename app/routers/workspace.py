# app/routers/workspace.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Workspace(BaseModel):
    id: str
    name: str

@router.get("/")
async def list_workspaces():
    # Replace with your logic to fetch workspaces from a database
    return [{"id": "1", "name": "My First Workspace"}]

@router.post("/")
async def create_workspace(workspace: Workspace):
    # Replace with logic to create and persist a workspace
    return workspace
