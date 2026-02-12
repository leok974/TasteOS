from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, desc
from datetime import datetime, date
from uuid import uuid4
from typing import List, Optional, Union

from .. import models, schemas
from ..deps import get_db, get_workspace
from ..parsing.ingredient_parser import normalize_ingredient

router = APIRouter()

# --- Helpers ---

def get_list_or_404(db: Session, list_id: str, workspace_id: str) -> models.GroceryList:
    lst = db.get(models.GroceryList, list_id)
    if not lst or lst.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Grocery list not found")
    return lst

def _aggregate_ingredient(agg, ing, recipe):
    """Helper to merge ingredient into aggregation map."""
    
    # Note: ing.qty is Decimal or float? In DB it says Numeric. Float conversion is safe for aggreg.
    qty_float = float(ing.qty) if ing.qty is not None else None
    
    norm_key, norm_display, norm_qty, norm_unit = normalize_ingredient(ing.name, qty_float, ing.unit)
    
    key = norm_key or ing.name.lower().strip()
    
    if key not in agg:
        agg[key] = {
            "display": norm_display or ing.name,
            "qty": 0.0,
            "unit": norm_unit or ing.unit,
            "sources": []
        }
    
    curr = agg[key]
    
    # Construct rough line representation since we don't store raw line in RecipeIngredient
    parts = []
    if ing.qty:
        # Use g formatting to avoid 1.0 being displayed as 1.0 but keep decimals for non-integers
        parts.append(f"{float(ing.qty):g}")
    if ing.unit:
        parts.append(ing.unit)
    parts.append(ing.name)
    line_str = " ".join(parts)

    # Append source
    source_entry = {
        "recipe_id": recipe.id,
        "recipe_title": recipe.title,
        "line": line_str 
    }
    
    # Check if duplicate source before adding
    is_duplicate_source = False
    for s in curr["sources"]:
        if s["recipe_id"] == recipe.id:
            is_duplicate_source = True
            break
    
    if not is_duplicate_source:
        curr["sources"].append(source_entry)
    
    # Sum logic
    # Only sum if units match (simple MVP)
    if norm_qty is not None:
        if curr["unit"] == norm_unit:
            curr["qty"] += norm_qty
        elif curr["qty"] == 0:
            # First non-zero qty wins unit (or fallback)
            curr["qty"] = norm_qty
            curr["unit"] = norm_unit


# --- List CRUD ---

@router.post("/lists", response_model=schemas.GroceryListOut)
def create_grocery_list(
    data: schemas.GroceryListCreate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Create a new empty grocery list."""
    new_list = models.GroceryList(
        workspace_id=workspace.id,
        title=data.title,
        kind=data.kind,
        source=None
    )
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    return new_list

@router.get("/lists", response_model=dict)
def get_grocery_lists(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get all grocery lists for workspace."""
    stmt = select(models.GroceryList).where(
        models.GroceryList.workspace_id == workspace.id
    ).order_by(desc(models.GroceryList.created_at))
    
    lists = db.execute(stmt).scalars().all()
    
    results = []
    for lst in lists:
        # Count items
        results.append({
            "id": lst.id,
            "title": lst.title,
            "kind": lst.kind,
            "created_at": lst.created_at,
            "updated_at": lst.updated_at,
            "item_count": len(lst.items) 
        })
    
    return {"lists": results}

@router.get("/lists/{list_id}", response_model=schemas.GroceryListOut)
def get_grocery_list_detail(
    list_id: str,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get full list details."""
    stmt = select(models.GroceryList).where(
        models.GroceryList.id == list_id,
        models.GroceryList.workspace_id == workspace.id
    ).options(selectinload(models.GroceryList.items))
    
    lst = db.execute(stmt).scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="Grocery list not found")
        
    return lst

@router.patch("/lists/{list_id}", response_model=schemas.GroceryListOut)
def update_grocery_list(
    list_id: str,
    data: schemas.GroceryListUpdate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    lst = get_list_or_404(db, list_id, workspace.id)
    if data.title is not None:
        lst.title = data.title
    lst.updated_at = datetime.now()
    db.commit()
    db.refresh(lst)
    return lst

@router.delete("/lists/{list_id}", status_code=204)
def delete_grocery_list(
    list_id: str,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    lst = get_list_or_404(db, list_id, workspace.id)
    db.delete(lst)
    db.commit()
    return 

# --- Item CRUD ---

@router.post("/lists/{list_id}/items", response_model=schemas.GroceryListItemOut)
def add_list_item(
    list_id: str,
    data: schemas.GroceryListItemCreate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    lst = get_list_or_404(db, list_id, workspace.id)
    
    key = data.key or data.display.lower().strip()
    
    # Determine position
    max_pos = db.execute(
        select(models.GroceryListItem.position)
        .where(models.GroceryListItem.list_id == list_id)
        .order_by(desc(models.GroceryListItem.position))
        .limit(1)
    ).scalar_one_or_none()
    
    next_pos = (max_pos + 1) if max_pos is not None else 0
    if data.position > 0: 
         next_pos = data.position

    item = models.GroceryListItem(
        list_id=lst.id,
        key=key,
        display=data.display,
        quantity=data.quantity,
        unit=data.unit,
        checked=data.checked,
        position=next_pos,
        raw=data.raw,
        sources=data.sources
    )
    db.add(item)
    lst.updated_at = datetime.now()
    db.commit()
    db.refresh(item)
    return item

@router.patch("/lists/{list_id}/items/{item_id}", response_model=schemas.GroceryListItemOut)
def update_list_item(
    list_id: str,
    item_id: str,
    data: schemas.GroceryListItemUpdate,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    # Ensure item belongs to workspace implicitly by checking list first?
    # Or just join...
    # Faster: Get item, check list.
    
    item = db.get(models.GroceryListItem, item_id)
    if not item:
         raise HTTPException(status_code=404, detail="Item not found")
         
    if item.list_id != list_id:
         raise HTTPException(status_code=404, detail="Item not in list")
    
    # Permissions via list
    lst = get_list_or_404(db, list_id, workspace.id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
        
    lst.updated_at = datetime.now()
    db.commit()
    db.refresh(item)
    return item

@router.delete("/lists/{list_id}/items/{item_id}", status_code=204)
def delete_list_item(
    list_id: str,
    item_id: str,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    lst = get_list_or_404(db, list_id, workspace.id)
    item = db.get(models.GroceryListItem, item_id)
    if not item or item.list_id != list_id:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(item)
    lst.updated_at = datetime.now()
    db.commit()
    return

# --- Generation ---

@router.post("/lists/generate", response_model=schemas.GroceryListOut)
def generate_grocery_list_v3(
    request: schemas.GroceryGenerateRequestV3,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Generate a list from Plan OR Recipes."""
    
    aggregated_items = {} # key -> { display, quantity, unit, ... }
    sources_meta = {}
    
    # A. From Plan
    if request.start:
        date_start = request.start
        stmt = select(models.MealPlan).options(
            selectinload(models.MealPlan.entries).selectinload(models.MealPlanEntry.recipe).selectinload(models.Recipe.ingredients)
        ).where(
            models.MealPlan.workspace_id == workspace.id,
            models.MealPlan.week_start == date_start
        )
        plan = db.execute(stmt).scalar_one_or_none()
        
        if plan:
            sources_meta["plan_id"] = plan.id
            for entry in plan.entries:
                if not entry.recipe: continue
                # Scope check
                if request.days and entry.date not in request.days: continue
                if request.meals and entry.meal_type not in request.meals: continue
                
                # Aggregate logic
                for ing in entry.recipe.ingredients:
                    _aggregate_ingredient(aggregated_items, ing, entry.recipe)

    # B. From Recipes
    if request.recipe_ids:
        recipes = db.execute(
            select(models.Recipe)
            .where(models.Recipe.id.in_(request.recipe_ids), models.Recipe.workspace_id == workspace.id)
            .options(selectinload(models.Recipe.ingredients))
        ).scalars().all()
        
        sources_meta["recipe_ids"] = [r.id for r in recipes]
        for recipe in recipes:
             for ing in recipe.ingredients:
                _aggregate_ingredient(aggregated_items, ing, recipe)

    # Create List
    new_list = models.GroceryList(
        workspace_id=workspace.id,
        title=request.title,
        kind="generated",
        source=sources_meta
    )
    db.add(new_list)
    db.flush()
    
    # Create Items
    sorted_keys = sorted(aggregated_items.keys())
    for idx, key in enumerate(sorted_keys):
        data = aggregated_items[key]
        item = models.GroceryListItem(
            list_id=new_list.id,
            key=key,
            display=data['display'],
            quantity=data['qty'] if data['qty'] > 0 else None,
            unit=data['unit'],
            position=idx,
            sources=data['sources'],
            checked=False
        )
        db.add(item)
    
    db.commit()
    
    stmt = select(models.GroceryList).where(models.GroceryList.id == new_list.id).options(selectinload(models.GroceryList.items))
    new_list = db.execute(stmt).scalar_one()

    return new_list
