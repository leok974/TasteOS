from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from app.models import Recipe, RecipeIngredient, PantryItem, PantryTransaction, CookSession
from app.schemas import PantryDecrementItem

def preview_decrement(db: Session, session: CookSession) -> list[PantryDecrementItem]:
    recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
    if not recipe:
        return []

    # Scaling
    recipe_servings = recipe.servings or 1
    session_servings = session.servings_target or recipe_servings
    scale = Decimal(session_servings) / Decimal(recipe_servings) if recipe_servings > 0 else Decimal(1)

    # Ingredients
    ingredients = db.scalars(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    ).all()
    
    results = []
    for ing in ingredients:
        # 1. Match Pantry Item (Simple Name Match)
        pantry_item = db.scalar(
            select(PantryItem).where(
                PantryItem.workspace_id == session.workspace_id,
                func.lower(PantryItem.name) == func.lower(ing.name)
            )
        )
        
        # 2. Calc qty needed
        qty_base = Decimal(ing.qty) if ing.qty is not None else Decimal(0)
        qty_needed = qty_base * scale
        
        # 3. Create preview item
        item = PantryDecrementItem(
            ingredient_name=ing.name,
            pantry_item_id=pantry_item.id if pantry_item else None,
            pantry_item_name=pantry_item.name if pantry_item else None,
            qty_needed=float(qty_needed),
            qty_available=float(pantry_item.qty) if pantry_item and pantry_item.qty is not None else None,
            unit=pantry_item.unit if pantry_item else (ing.unit or ""),
            match_confidence=1.0 if pantry_item else 0.0
        )
        results.append(item)
        
    return results

def apply_decrement(db: Session, session: CookSession, items: list[PantryDecrementItem]):
    # Idempotency handled by router ideally (transaction boundary)
    
    for item in items:
        if not item.pantry_item_id:
            continue
            
        p_item = db.scalar(select(PantryItem).where(PantryItem.id == item.pantry_item_id))
        if not p_item:
            continue
            
        # Delta
        delta = Decimal(str(item.qty_needed)) # float to decimal safety
        if delta == 0:
            continue
            
        # Create Transaction
        txn = PantryTransaction(
            workspace_id=session.workspace_id,
            pantry_item_id=p_item.id,
            source="cook",
            ref_type="cook_session",
            ref_id=session.id,
            delta_qty=-delta, # Decrement
            unit=item.unit,
            note=f"Cooked session"
        )
        db.add(txn)
        
        # Update Item
        current_qty = p_item.qty if p_item.qty is not None else Decimal(0)
        new_qty = max(Decimal(0), current_qty - delta)
        p_item.qty = new_qty
        
    db.flush()

def undo_decrement(db: Session, session: CookSession):
    # Find transactions
    txns = db.scalars(
        select(PantryTransaction).where(
            PantryTransaction.ref_type == "cook_session",
            PantryTransaction.ref_id == session.id,
            PantryTransaction.undone_at.is_(None)
        )
    ).all()
    
    now = datetime.now(timezone.utc)
    
    for txn in txns:
        p_item = db.scalar(select(PantryItem).where(PantryItem.id == txn.pantry_item_id))
        if p_item:
            # Restore
            p_item.qty = (p_item.qty or Decimal(0)) - txn.delta_qty
            
        txn.undone_at = now
        
    db.flush()
