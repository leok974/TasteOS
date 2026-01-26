
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
            # Loop v2: Exclude explicit leftovers
            plan_ids = [
                e.recipe_id for e in plan.entries 
                if e.recipe_id and not e.is_leftover
            ]
            
            # Loop v2: Exclude recipes that have active leftovers in fridge
            # (Heuristic: If I have leftovers, I eat them instead of cooking)
            from sqlalchemy import select
            active_leftover_recipe_ids = db.scalars(
                select(models.Leftover.recipe_id).where(
                    models.Leftover.workspace_id == workspace.id,
                    models.Leftover.consumed_at.is_(None),
                    models.Leftover.recipe_id.is_not(None)
                )
            ).all()
            active_leftover_set = set(active_leftover_recipe_ids)
            
            # Filter out recipes present in leftovers
            # (Only applies to plan generated items, or manual ones too? 
            # Prompt says "generating from plan".
            plan_ids = [rid for rid in plan_ids if rid not in active_leftover_set]
            
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
        
    old_status = item.status
    
    if update.status:
        item.status = update.status
    if update.qty is not None:
        item.qty = update.qty
        
    # Hook: Purchased -> Pantry Sync
    if update.status == "purchased" and old_status != "purchased":
        sync_purchased_item_to_pantry(db, workspace, item)
        
    db.commit()
    db.refresh(item)
    return item

def sync_purchased_item_to_pantry(db: Session, workspace: models.Workspace, item: models.GroceryListItem):
    """Sync a purchased grocery item to the pantry (Idempotent)."""
    from datetime import datetime
    
    # 1. Idempotency check: Already linked?
    if item.pantry_item_id:
        return # Already synced
        
    # 2. Normalize Name
    # Simple logic: lowercase, strip. Advanced: use LLM or robust fuzzy logic (saved for v2)
    normalized_name = item.name.strip().lower()
    
    # 3. Find existing pantry item
    # Note: Using func.lower() on the DB side is safer
    from sqlalchemy import func
    pantry_item = db.query(models.PantryItem).filter(
        models.PantryItem.workspace_id == workspace.id,
        func.lower(models.PantryItem.name) == normalized_name
    ).first()
    
    now = datetime.now()
    
    if pantry_item:
        # Update existing
        # If we tracked distinct quantities effectively, we'd add here. 
        # For v1 MVP: just update the timestamp to show it was refreshed. 
        # Optionally, we could assume if grocery said 500g, we add 500g. 
        # But units often mismatch (packet vs grams). 
        # Strategy: Valid loop v1 -> Just mark it as "restocked" (last_used/updated)
        pantry_item.updated_at = now
        # If pantry item has 0 qty, reset to default? Let's leave quantity logic for v2.
    else:
        # Create new
        pantry_item = models.PantryItem(
            workspace_id=workspace.id,
            name=item.name, # Keep original casing (or Title Case)
            qty=item.qty,
            unit=item.unit,
            category=item.category,
            source="grocery",
            created_at=now,
            updated_at=now
        )
        db.add(pantry_item)
        db.flush() # Get ID
        
    # 4. Link & Timestamp
    item.pantry_item_id = pantry_item.id
    item.purchased_at = now
    # Store snapshot of purchase amounts
    item.qty_purchased = item.qty
    item.unit_purchased = item.unit

@router.post("/current/sync-to-pantry")
def sync_current_list_to_pantry(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Bulk sync purchased items from current list to pantry."""
    # Get current list
    grocery_list = db.query(models.GroceryList).filter(
        models.GroceryList.workspace_id == workspace.id
    ).order_by(models.GroceryList.created_at.desc()).first()
    
    if not grocery_list:
        raise HTTPException(status_code=404, detail="No active grocery list found")
    
    synced_count = 0
    skipped_count = 0
    
    # Find purchsaed items not yet synced
    items_to_sync = [
        i for i in grocery_list.items 
        if i.status == "purchased" and not i.pantry_item_id
    ]
    
    for item in items_to_sync:
        sync_purchased_item_to_pantry(db, workspace, item)
        synced_count += 1
        
    db.commit()
    
    return {
        "synced": synced_count,
        "skipped": len([i for i in grocery_list.items if i.status == "purchased"]) - synced_count,
        "total_purchased": len([i for i in grocery_list.items if i.status == "purchased"])
    }
