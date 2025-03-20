# app/routers/model.py
import uuid
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.model import Model
from app.schemas.model import ModelNewResponse

router = APIRouter()

@router.post("/new", response_model=ModelNewResponse)
def create_model(
    user_id: str = Form(...),
    name: str = Form(...),
    ak: str = Form(...),
    base_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Create a new model configuration.
    
    - **user_id**: The ID of the user adding this model.
    - **name**: The name of the model.
    - **ak**: The API key for the model.
    - **base_url**: The base URL for the model’s API.
    
    Returns the new model details including its generated ID.
    """
    model_id = str(uuid.uuid4())
    new_model = Model(
        id=model_id,
        name=name,
        ak=ak,
        base_url=base_url,
        user_id=user_id
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    return ModelNewResponse(
        id=new_model.id,
        name=new_model.name,
        base_url=new_model.base_url,
        user_id=new_model.user_id
    )

@router.delete("/delete/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)):
    """
    Delete an existing model configuration by its model_id.
    
    Returns a confirmation message upon successful deletion.
    """
    model_obj = db.query(Model).filter(Model.id == model_id).first()
    if not model_obj:
        raise HTTPException(status_code=404, detail="Model not found.")
    
    db.delete(model_obj)
    db.commit()
    return {"detail": "Model deleted successfully."}
