"""Grocery List Agent."""
from typing import Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Workspace, Recipe, GroceryList, GroceryListItem, PantryItem

def generate_grocery_list(
    db: Session,
    workspace: Workspace,
    recipe_ids: Optional[list[str]] = None,
    source_override: Optional[str] = None,
    recipe_scaling: Optional[dict[str, float]] = None
) -> GroceryList:
    """Generate a grocery list from selected recipes."""
    recipe_scaling = recipe_scaling or {}
    
    # 0. Fetch Previous List Context (to persist manual overrides)
    # We look for the most recent list to see if user marked things as "have" or "purchased"
    last_list = db.query(GroceryList).filter(
        GroceryList.workspace_id == workspace.id
    ).order_by(desc(GroceryList.created_at)).first()
    
    previous_status_map = {}
    if last_list:
        print(f"DEBUG_GROCERY: Found previous list {last_list.id} from {last_list.created_at}", flush=True)
        # Load items
        # items might be lazy loaded, accessing them should trigger it if session is active
        for item in last_list.items:
            # We care if they marked it as 'have' or 'purchased' or 'optional'
            # If they marked it 'need', we re-eval based on pantry anyway.
            # But if they explicitly moved it to 'have' (excluded), we want to remember that.
            if item.status in ['have', 'purchased']:
                print(f"DEBUG_GROCERY: Previous item '{item.name}' status is '{item.status}' reason='{item.reason}'", flush=True)
                previous_status_map[item.name.lower()] = {
                    "status": item.status,
                    "reason": item.reason
                }
    else:
        print("DEBUG_GROCERY: No previous list found.", flush=True)

    # 1. Collect Ingredients
    ingredients_to_buy = []
    
    if recipe_ids:
        # Fetch recipes with ingredients
        recipes = db.query(Recipe).filter(
            Recipe.id.in_(recipe_ids),
            Recipe.workspace_id == workspace.id
        ).all()
        
        for recipe in recipes:
            scale = recipe_scaling.get(recipe.id, 1.0)
            for ing in recipe.ingredients:
                # Create a lightweight dict or object to represent the need
                needed_qty = (float(ing.qty) * scale) if ing.qty is not None else None
                ingredients_to_buy.append({
                    "name": ing.name,
                    "qty": needed_qty,
                    "unit": ing.unit,
                    "category": ing.category
                })
                
    # 2. Get Pantry Items
    pantry_items = db.query(PantryItem).filter(
        PantryItem.workspace_id == workspace.id
    ).all()
    
    pantry_map = {p.name.lower(): p for p in pantry_items}
    
    # 3. Create List Record
    # Delete existing lists first to ensure we don't pile up lists
    db.query(GroceryList).filter(GroceryList.workspace_id == workspace.id).delete(synchronize_session=False)
    db.commit() # Ensure previous lists are gone
    
    source_ref = source_override or (f"recipes:{','.join(sorted(recipe_ids))}" if recipe_ids else "manual")
    
    grocery_list = GroceryList(
        workspace_id=workspace.id,
        source=source_ref
    )
    db.add(grocery_list)
    db.flush() # get ID
    
    # 4. Aggregate Items
    aggregated = {} # name_lower -> {name, qty, unit, category}
    
    for ing in ingredients_to_buy:
        key = ing["name"].lower()
        if key in aggregated:
            # Simple unit check - sum if units match
            if aggregated[key]['unit'] == ing["unit"]:
                 aggregated[key]['qty'] = (aggregated[key]['qty'] or 0) + (ing["qty"] or 0)
        else:
            aggregated[key] = {
                "name": ing["name"], 
                "qty": ing["qty"] if ing["qty"] else 0,
                "unit": ing["unit"],
                "category": ing["category"]
            }
            
    # 5. Create List Items (Compare with Pantry)
    # Track carryovers for meta
    carryover_items = []

    for key, data in aggregated.items():
        status = "need"
        reason = "Missing from pantry"
        
        # 0. Check Previous List Override (For Meta Tracking ONLY, no longer forces 'have')
        if key in previous_status_map:
            prev_info = previous_status_map[key]
            # Add to carryover meta if it was manually excluded/purchased
            carryover_items.append({
                "name": data["name"],
                "reason": prev_info.get("reason"),
                "status": prev_info.get("status")
            })
        
        # 1. Pantry Check (This is the ONLY source of truth for 'have' now, per user request)
        if key in pantry_map:
            pitem = pantry_map[key]
            status = "have"
            reason = f"Pantry match: {pitem.name}"
        else:
             # Contains match logic
            for p_name, p_item in pantry_map.items():
                if p_name in key or key in p_name:
                    status = "have"
                    reason = f"Pantry match: {p_item.name}"
                    break
        
        item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            name=data["name"],
            qty=data["qty"] if data["qty"] > 0 else None,
            unit=data["unit"],
            category=data["category"],
            status=status,
            reason=reason
        )
        db.add(item)
        
    db.commit()
    db.refresh(grocery_list)
    
    # Re-populate transient expiry for immediate return
    today = date.today()
    for item in grocery_list.items:
        key = item.name.lower()
        matched = None
        if key in pantry_map:
            matched = pantry_map[key]
        else:
            for p_name, p_item in pantry_map.items():
                if p_name in key or key in p_name:
                    matched = p_item
                    break
        
        if matched and matched.expires_on:
            item.expiry_days = (matched.expires_on - today).days
    
    # Attach tracking prop to object temporarily (hack to pass to router)
    grocery_list._carryover_items = carryover_items
    
    return grocery_list
