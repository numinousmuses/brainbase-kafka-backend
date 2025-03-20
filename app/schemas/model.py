# app/schemas/model.py
from pydantic import BaseModel

class ModelNewResponse(BaseModel):
    id: str
    name: str
    base_url: str
    user_id: str
