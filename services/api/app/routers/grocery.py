
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_workspace
from ..agents.grocery_agent import generate_grocery_list

router = APIRouter()

@router.post("/generate", response_model=schemas.GroceryListOut)
def generate_list(
    request: schemas.GenerateGroceryRequest,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Generate a new grocery list based on recipes."""
    recipe_ids = request.recipe_ids[:]
    source_override = None
    
    if request.plan_id:
        # Get plan
        plan = db.query(models.MealPlan).filter(models.MealPlan.id == request.plan_id).first()
        if plan:
            plan_ids = [e.recipe_id for e in plan.entries if e.recipe_id]
            recipe_ids.extend(plan_ids)
            source_override = f"plan:{request.plan_id}"
            
        # Dedupe
        recipe_ids = list(set(recipe_ids))
    
    # Logic delegated to agent
    grocery_list = generate_grocery_list(
        db=db,
        workspace=workspace,
        recipe_ids=recipe_ids,
        source_override=source_override
    )
    return grocery_list

@router.get("/current", response_model=schemas.GroceryListOut)
def get_current_list(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get the most recent grocery list."""
    grocery_list = db.query(models.GroceryList).filter(
        models.GroceryList.workspace_id == workspace.id
    ).order_by(models.GroceryList.created_at.desc()).first()
    
    if not grocery_list:
        raise HTTPException(status_code=404, detail="No active grocery list found")
        
    return grocery_list

@router.patch("/items/{item_id}", response_model=schemas.GroceryListItemOut)
def update_item_status(
    item_id: str,
    update: schemas.GroceryItemUpdate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Update item status or quantity."""
    # Join to ensure workspace isolation via list
    item = db.query(models.GroceryListItem).join(models.GroceryList).filter(
        models.GroceryListItem.id == item_id,
        models.GroceryList.workspace_id == workspace.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if update.status:
        item.status = update.status
    if update.qty is not None:
        item.qty = update.qty
        
    db.commit()
    db.refresh(item)
    return item
