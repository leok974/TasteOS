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
        # Expires soon (<= 5 days from now) or already expired, OR generic use_soon_at date matches
        query = query.filter(
            (models.PantryItem.expires_on != None) & (models.PantryItem.expires_on <= expires_threshold) 
            | (models.PantryItem.use_soon_at != None) & (models.PantryItem.use_soon_at <= today)
        ).order_by(models.PantryItem.expires_on.asc().nulls_last())
    else:
        query = query.order_by(models.PantryItem.created_at.desc())
        
    return query.limit(limit).offset(offset).all()

@router.get("/use-soon", response_model=list[schemas.PantryItemOut])
def get_use_soon_items(
    days: int = Query(5, ge=1, le=30),
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Specific endpoint for 'Use Soon' items."""
    today = date.today()
    expires_threshold = today + timedelta(days=days)
    
    query = db.query(models.PantryItem).filter(
        models.PantryItem.workspace_id == workspace.id,
        (
            ((models.PantryItem.expires_on != None) & (models.PantryItem.expires_on <= expires_threshold)) |
            ((models.PantryItem.use_soon_at != None) & (models.PantryItem.use_soon_at <= today))
        )
    ).order_by(models.PantryItem.expires_on.asc().nulls_last())
    
    return query.all()

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
    
    # Store old qty for transaction logic
    old_qty = item.qty
        
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    # Track Quantity Changes
    if 'qty' in update_data:
        q_old = float(old_qty or 0.0)
        q_new = float(item.qty or 0.0)
        # simple float comparison with epsilon or just straight up 
        if abs(q_new - q_old) > 0.0001: 
            txn = models.PantryTransaction(
                workspace_id=workspace.id,
                pantry_item_id=item.id,
                source="manual",
                ref_type="manual",
                ref_id=None,
                delta_qty=q_new - q_old,
                unit=item.unit,
                note="Manual update"
            )
            db.add(txn)
        
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


# --- Leftovers ---

from ..services.leftover_service import create_leftover_for_entry

@router.post("/leftovers", response_model=schemas.LeftoverOut)
def create_leftover(
    leftover_in: schemas.LeftoverCreate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Create a leftover tracking entry and sync to pantry."""
    leftover = create_leftover_for_entry(
        db=db,
        workspace=workspace,
        plan_entry_id=leftover_in.plan_entry_id,
        recipe_id=leftover_in.recipe_id,
        name=leftover_in.name,
        servings=float(leftover_in.servings_left) if leftover_in.servings_left else 1.0,
        notes=leftover_in.notes
    )
    
    db.commit()
    db.refresh(leftover)
    return leftover

@router.get("/leftovers", response_model=list[schemas.LeftoverOut])
def get_leftovers(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get active leftovers."""
    return db.query(models.Leftover).filter(
        models.Leftover.workspace_id == workspace.id,
        models.Leftover.consumed_at.is_(None)
    ).all()
