
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from datetime import date, datetime

from .. import models, schemas
from ..deps import get_db, get_workspace
from ..agents.grocery_agent import generate_grocery_list
from ..parsing.ingredient_parser import normalize_ingredient, parse_ingredient_line

router = APIRouter()

@router.post("/generate-plan", response_model=schemas.GroceryV2Response)
def generate_grocery_list_from_plan(
    request: schemas.GroceryGenerateV2Request,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Generate a deterministic grocery list from the weekly plan."""
    
    # 1. Fetch Plan
    # Calculate Monday just in case, though we expect week_start to be Monday
    monday = request.start - date.fromtimestamp(0).replace(day=1).min # logic error
    # Actually just assume request.start is correct or normalize
    # Let's trust input for now, or normalize to Monday
    week_start = request.start
    
    stmt = select(models.MealPlan).options(
        selectinload(models.MealPlan.entries).selectinload(models.MealPlanEntry.recipe).selectinload(models.Recipe.ingredients)
    ).where(
        models.MealPlan.workspace_id == workspace.id,
        models.MealPlan.week_start == week_start
    )
    plan = db.execute(stmt).scalar_one_or_none()
    
    aggregated_items = {} # key -> { display, quantity, unit, raw[], sources[] }
    unparsed_items = []

    if plan:
        # 2. Iterate Entries
        for entry in plan.entries:
            if not entry.recipe: continue
            
            # Filter by Day
            if request.days and entry.date not in request.days:
                continue
            
            # Filter by Meal
            if request.meals and entry.meal_type not in request.meals:
                continue
                
            recipe = entry.recipe
            
            # 3. Process Ingredients
            # Priority: RecipeIngredient (structured) -> Fallback (parsing step text? No, instructions say 'lightweight parser')
            # But C2 says 'Input: ingredient line string'.
            # If we have structured ingredients, we construct the string for 'raw' or use them directly.
            
            if recipe.ingredients:
                for ing in recipe.ingredients:
                    # Construct pseudo-raw for checks
                    raw_str = f"{ing.qty or ''} {ing.unit or ''} {ing.name}".strip()
                    
                    key, display, qty, unit = normalize_ingredient(ing.name, float(ing.qty) if ing.qty else None, ing.unit)
                    
                    if key not in aggregated_items:
                        aggregated_items[key] = {
                            "key": key,
                            "display": display,
                            "quantity": 0.0,
                            "unit": unit,
                            "raw": [],
                            "sources": []
                        }
                    
                    agg = aggregated_items[key]
                    
                    # Unit mismatch check (simple: if match, add. If not, maybe keep separate? For V1, just add if unit matches or is None)
                    if agg["unit"] == unit:
                        if qty: agg["quantity"] += qty
                    else:
                        # If unit mismatch, we might want to flag it or just append to raw.
                        # V1: Ignore unit conversion, just append raw line.
                        pass
                        
                    agg["raw"].append(raw_str)
                    agg["sources"].append({
                        "recipe_id": recipe.id,
                        "recipe_title": recipe.title,
                        "line": raw_str
                    })
            else:
                # No structured ingredients? 
                # Could parse `steps` if ingredients are missing? 
                # Or `variants`? 
                # For V1, if no ingredients, we can't do much.
                pass

    # 4. Format Output
    items_out = []
    for k, v in aggregated_items.items():
        # Round quantity
        if v["quantity"] > 0:
            v["quantity"] = round(v["quantity"], 2)
        else:
            v["quantity"] = None
            
        items_out.append(schemas.GroceryItemV2(**v))
    
    # Sort by display name
    items_out.sort(key=lambda x: x.display)

    # 5. Persist to Database (Fix for 404 on /grocery)
    # Clear existing lists for this workspace to avoid confusion
    db.query(models.GroceryList).filter(models.GroceryList.workspace_id == workspace.id).delete()
    
    # Create new container
    new_list = models.GroceryList(
        workspace_id=workspace.id,
        source=f"plan:{week_start}",
        created_at=datetime.now()
    )
    db.add(new_list)
    db.flush()
    
    # Map V2 items to DB items
    db_items = []
    for item in items_out:
        db_item = models.GroceryListItem(
            grocery_list_id=new_list.id,
            name=item.display,
            qty=item.quantity,
            unit=item.unit,
            category="Uncategorized", 
            status="need"
        )
        db_items.append(db_item)
        
    db.add_all(db_items)
    db.commit()

    return schemas.GroceryV2Response(
        scope=schemas.GroveryV2Scope(
            start=request.start,
            days=request.days,
            meals=request.meals
        ),
        items=items_out,
        unparsed=unparsed_items # Populated if parsing failed (not implemented for structured input path)
    )

@router.post("/generate", response_model=schemas.GroceryGenerateResponse)
def generate_list(
    request: schemas.GenerateGroceryRequest,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Generate a new grocery list based on recipes."""
    recipe_ids = request.recipe_ids[:] # Start with manually passed IDs
    source_override = None
    
    # Meta tracking
    skipped_entries = []
    reduced_recipes = []
    included_count = 0
    skipped_count = 0
    recipe_scaling = {} # recipe_id -> factor
    
    print(f"DEBUG: Generating Grocery List. PlanID={request.plan_id}, IncludeEntries={request.include_entry_ids}")
    print(f"DEBUG: Recipe IDs passed explicitly: {len(request.recipe_ids)} count. First few: {request.recipe_ids[:3]}")

    if request.plan_id:
        # Get plan with explicit loading
        stmt = select(models.MealPlan).options(
            selectinload(models.MealPlan.entries)
        ).where(models.MealPlan.id == request.plan_id)
        
        plan = db.execute(stmt).scalar_one_or_none()
        
        if plan:
            print(f"DEBUG: Found plan {plan.id}. Entries count: {len(plan.entries)}")
            # 1. Fetch Active Leftovers Map
            # from sqlalchemy import select  # Removed redundant local import that shadows outer scope
            active_leftovers = db.scalars(
                select(models.Leftover).where(
                    models.Leftover.workspace_id == workspace.id,
                    models.Leftover.consumed_at.is_(None),
                    models.Leftover.recipe_id.is_not(None)
                )
            ).all()
            
            # Use dictionary for easier lookup: recipe_id -> Leftover
            # Warning: Could have multiple leftovers for same recipe. Use most recent or sum?
            # For simplicity, taking the first one found or summing servings.
            # Let's map recipe_id -> list[Leftover]
            leftover_map = {}
            for lo in active_leftovers:
                if lo.recipe_id not in leftover_map:
                    leftover_map[lo.recipe_id] = []
                leftover_map[lo.recipe_id].append(lo)
            
            # 2. Iterate Entries
            for entry in plan.entries:
                print(f"DEBUG: Checking Entry {entry.id} (Type {entry.meal_type}). RecipeID={entry.recipe_id}")
                if not entry.recipe_id:
                    continue
                    
                rid = entry.recipe_id
                
                # Check Overrides
                explicitly_included = (
                    entry.force_cook 
                    or str(entry.id) in request.include_entry_ids 
                    or str(rid) in request.include_recipe_ids
                )
                
                print(f"DEBUG: Entry {entry.id} (Recipe {rid}). Explicit={explicitly_included}. Leftover={entry.is_leftover}")
                
                should_skip = False
                skip_reason = None
                reduction_factor = 1.0
                
                if explicitly_included:
                    should_skip = False
                else:
                    # Logic 1: Explicit Leftover Plan (Always skip unless explicitly included)
                    if entry.is_leftover:
                        should_skip = True
                        skip_reason = "entry_marked_leftover"
                    
                    # Logic 2: Active Leftover (Skip unless ignored)
                    elif rid in leftover_map and not request.ignore_leftovers:
                        # Check servings math
                        los = leftover_map[rid]
                        total_left = sum([float(lo.servings_left or 0) for lo in los])
                        
                        # We need planned servings to compare.
                        # If entry has scaling or recipe has servings.
                        # Assuming recipe default for now (or 4.0 hardcoded if missing, need access to Recipe)
                        # We need to fetch recipe to be accurate.
                        recipe = db.get(models.Recipe, rid)
                        planned_servings = float(recipe.servings or 4.0)
                        
                        if total_left >= planned_servings:
                            should_skip = True
                            skip_reason = "active_leftover_exists"
                        elif total_left > 0:
                            # Partial reduction
                            reduction_factor = max(0.0, (planned_servings - total_left) / planned_servings)
                            # Log it
                            reduced_recipes.append(schemas.GroceryReducedRecipe(
                                recipe_id=rid,
                                title=recipe.title,
                                factor=reduction_factor,
                                reason="partial_leftovers"
                            ))
                            
                if should_skip:
                    skipped_count += 1
                    # Need title for meta
                    title = "Unknown Recipe"
                    # Try to get title without heavy query if possible, or single query
                    # existing: entry.recipe (might be detached or None)
                    r = db.get(models.Recipe, rid)
                    if r: title = r.title
                    
                    skipped_entries.append(schemas.GrocerySkippedEntry(
                        plan_entry_id=entry.id,
                        recipe_id=rid,
                        title=title,
                        reason=skip_reason or "unknown"
                    ))
                else:
                    included_count += 1
                    recipe_ids.append(rid)
                    if reduction_factor < 1.0:
                        recipe_scaling[rid] = reduction_factor
            
            source_override = f"plan:{request.plan_id}"
            
        # Dedupe recipe_ids
        recipe_ids = list(set(recipe_ids))
    
    # Logic delegated to agent
    grocery_list = generate_grocery_list(
        db=db,
        workspace=workspace,
        recipe_ids=recipe_ids,
        source_override=source_override,
        recipe_scaling=recipe_scaling
    )

    # Agent handles commit/refresh
    
    # Build Meta
    # Extract hacked carryover prop
    carryover = getattr(grocery_list, "_carryover_items", [])
    
    meta = schemas.GroceryGenerationMeta(
        included_count=included_count,
        skipped_count=skipped_count,
        skipped_entries=skipped_entries,
        reduced_recipes=reduced_recipes,
        carryover_items=carryover
    )
    
    return schemas.GroceryGenerateResponse(list=grocery_list, meta=meta)

@router.get("/current", response_model=schemas.GroceryListOut)
def get_current_list(
    recompute: bool = False,
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get the most recent grocery list."""
    grocery_list = db.query(models.GroceryList).filter(
        models.GroceryList.workspace_id == workspace.id
    ).order_by(models.GroceryList.created_at.desc()).first()
    
    if not grocery_list:
        raise HTTPException(status_code=404, detail="No active grocery list found")
        
    if recompute:
        from sqlalchemy import func
        # Re-check pantry items
        pantry_items = db.query(models.PantryItem).filter(
            models.PantryItem.workspace_id == workspace.id
        ).all()
        pantry_map = {p.name.lower(): p for p in pantry_items}
        
        today = date.today()
        changes = 0
        
        # Pass 1: DB Updates (Status Sync)
        for item in grocery_list.items:
            key = item.name.lower()
            matched_item = None
            
            if key in pantry_map:
                matched_item = pantry_map[key]
            else:
                 # Fuzzy check
                for p_name, p_item in pantry_map.items():
                    if p_name in key or key in p_name:
                        matched_item = p_item
                        break
            
            if matched_item:
                # Logic: If status="need" AND in_pantry -> "have"
                if item.status == "need":
                    item.status = "have"
                    item.reason = f"Pantry match: {matched_item.name}"
                    changes += 1
            else:
                # Logic: If status="have" (Pantry Match) AND NOT in_pantry -> "need"
                if item.status == "have" and "Pantry match" in (item.reason or ""):
                    item.status = "need"
                    item.reason = "Missing from pantry (recompute)"
                    changes += 1
        
        if changes > 0:
            db.commit()
            db.refresh(grocery_list)
            
        # Pass 2: Transient Attributes (Calculated after potential DB refresh)
        for item in grocery_list.items:
            key = item.name.lower()
            matched_item = None
             # Re-match (fast enough)
            if key in pantry_map: matched_item = pantry_map[key]
            else:
                for p_name, p_item in pantry_map.items():
                    if p_name in key or key in p_name:
                        matched_item = p_item
                        break
            
            if matched_item and matched_item.expires_on:
                item.expiry_days = (matched_item.expires_on - today).days

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

@router.delete("/current", status_code=204)
def clear_current_list(
    workspace: models.Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Delete ALL grocery lists for the workspace to ensure a clean slate."""
    print(f"DEBUG: DELETE /current called for workspace {workspace.id}", flush=True)
    
    db.query(models.GroceryList).filter(
        models.GroceryList.workspace_id == workspace.id
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return
