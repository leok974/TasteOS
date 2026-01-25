"""Grocery List Agent."""
from typing import Optional
from sqlalchemy.orm import Session
from ..models import Workspace, Recipe, GroceryList, GroceryListItem, PantryItem

def generate_grocery_list(
    db: Session,
    workspace: Workspace,
    recipe_ids: Optional[list[str]] = None,
    source_override: Optional[str] = None
) -> GroceryList:
    """Generate a grocery list from selected recipes."""
    
    # 1. Collect Ingredients
    ingredients_to_buy = []
    
    if recipe_ids:
        # Fetch recipes with ingredients
        recipes = db.query(Recipe).filter(
            Recipe.id.in_(recipe_ids),
            Recipe.workspace_id == workspace.id
        ).all()
        
        for recipe in recipes:
            for ing in recipe.ingredients:
                ingredients_to_buy.append(ing)
                
    # 2. Get Pantry Items
    pantry_items = db.query(PantryItem).filter(
        PantryItem.workspace_id == workspace.id
    ).all()
    
    pantry_map = {p.name.lower(): p for p in pantry_items}
    
    # 3. Create List Record
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
        key = ing.name.lower()
        if key in aggregated:
            # Simple unit check - sum if units match
            if aggregated[key]['unit'] == ing.unit:
                 aggregated[key]['qty'] = (aggregated[key]['qty'] or 0) + (ing.qty or 0)
        else:
            aggregated[key] = {
                "name": ing.name, 
                "qty": ing.qty if ing.qty else 0,
                "unit": ing.unit,
                "category": ing.category
            }
            
    # 5. Create List Items (Compare with Pantry)
    for key, data in aggregated.items():
        status = "need"
        reason = "Missing from pantry"
        
        # Exact match
        if key in pantry_map:
            pitem = pantry_map[key]
            status = "have"
            reason = f"Pantry has {pitem.qty or ''} {pitem.unit or ''}"
        else:
            # Contains match logic (Pantry has "Milk", Ingredient is "Whole Milk")
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
    return grocery_list
