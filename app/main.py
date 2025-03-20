# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, workspace, chat, file, model
from app.core.database import init_db

app = FastAPI()

# Add CORS middleware (adjust allow_origins as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(workspace.router, prefix="/workspace", tags=["Workspace"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(file.router, prefix="/file", tags=["File"])
app.include_router(model.router, prefix="/models", tags=["Model"])

# Initialize the database (create tables if needed)
init_db()

# Optionally, add a simple root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI backend!"}