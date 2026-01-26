from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.models import Leftover, PantryItem, Workspace
from decimal import Decimal

def create_leftover_for_entry(
    db: Session, 
    workspace: Workspace, 
    plan_entry_id: str, 
    recipe_id: str, 
    name: str, 
    servings: float = 1.0, 
    notes: str = None
):
    """
    Creates a Leftover record (and PantryItem) for a Meal Plan Entry.
    Idempotent: returns existing active leftover if present.
    """
    # Dedupe check
    existing = db.scalar(
        select(Leftover).where(
            Leftover.workspace_id == workspace.id,
            Leftover.plan_entry_id == plan_entry_id,
            Leftover.consumed_at.is_(None)
        )
    )
    
    if existing:
        return existing

    # Default expiry: 3 days
    expires_on = date.today() + timedelta(days=3)

    # 1. Create Pantry Item First (to simulate "From Pantry")
    # Actually, we usually create both.
    
    pantry_item = PantryItem(
        workspace_id=workspace.id,
        name=name,
        qty=float(servings), # DB is Numeric, but Pydantic might expect float
        unit="servings",
        category="Leftovers",
        expires_on=expires_on,
        source="leftover",
        notes=notes
    )
    db.add(pantry_item)
    db.flush()
    
    # 2. Create Leftover Record
    leftover = Leftover(
        workspace_id=workspace.id,
        plan_entry_id=plan_entry_id,
        recipe_id=recipe_id,
        pantry_item_id=pantry_item.id,
        name=name,
        expires_on=expires_on,
        servings_left=Decimal(servings),
        notes=notes
    )
    db.add(leftover)
    db.flush()
    
    return leftover
