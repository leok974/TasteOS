from typing import List
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime

from ..db import get_db
from ..models import Workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceRead(BaseModel):
    id: str
    slug: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

def generate_slug(name: str) -> str:
    # Convert to lowercase, replace spaces/symbols with hyphens
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug or "workspace"

@router.get("/", response_model=List[WorkspaceRead])
def list_workspaces(db: Session = Depends(get_db)):
    """List all workspaces sorted by creation date."""
    return db.query(Workspace).order_by(Workspace.created_at).all()

@router.post("/", response_model=WorkspaceRead)
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db)
):
    """Create a new workspace with auto-generated slug."""
    slug_base = generate_slug(data.name)
    slug = slug_base
    
    # Simple retry logic for slug uniqueness (append counter if needed)
    counter = 1
    while True:
        existing = db.query(Workspace).filter(Workspace.slug == slug).first()
        if not existing:
            break
        slug = f"{slug_base}-{counter}"
        counter += 1
        
    workspace = Workspace(
        name=data.name,
        slug=slug
    )
    
    try:
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create workspace")
