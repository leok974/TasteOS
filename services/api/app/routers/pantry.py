from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..deps import get_db, get_workspace

router = APIRouter()

@router.get("/", response_model=list[schemas.PantryItemOut])
def get_pantry_items(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    use_soon: bool = False,
    limit: int = 100,
    offset: int = 0
):
    """List pantry items with optional filtering."""
    query = db.query(models.PantryItem).filter(models.PantryItem.workspace_id == workspace.id)
    
    if q:
        query = query.filter(func.lower(models.PantryItem.name).contains(q.lower()))
        
    if use_soon:
        today = date.today()
        expires_threshold = today + timedelta(days=5)
        # Expires soon (<= 5 days from now) or already expired
        query = query.filter(
            models.PantryItem.expires_on.isnot(None),
            models.PantryItem.expires_on <= expires_threshold
        ).order_by(models.PantryItem.expires_on.asc())
    else:
        query = query.order_by(models.PantryItem.created_at.desc())
        
    return query.limit(limit).offset(offset).all()

@router.post("/", response_model=schemas.PantryItemOut, status_code=status.HTTP_201_CREATED)
def create_pantry_item(
    item_in: schemas.PantryItemCreate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Create a new pantry item."""
    item = models.PantryItem(
        **item_in.model_dump(),
        workspace_id=workspace.id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.patch("/{item_id}", response_model=schemas.PantryItemOut)
def update_pantry_item(
    item_id: str,
    item_in: schemas.PantryItemUpdate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Update a pantry item."""
    item = db.query(models.PantryItem).filter(
        models.PantryItem.id == item_id,
        models.PantryItem.workspace_id == workspace.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Pantry item not found")
        
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
        
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pantry_item(
    item_id: str,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Delete a pantry item."""
    item = db.query(models.PantryItem).filter(
        models.PantryItem.id == item_id,
        models.PantryItem.workspace_id == workspace.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Pantry item not found")
        
    db.delete(item)
    db.commit()
