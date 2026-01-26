
from datetime import date, timedelta, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models import MealPlan, MealPlanEntry, Recipe, Workspace
from ..agents.planner_agent import generate_week_plan
from ..deps import get_workspace

router = APIRouter()

# --- Schemas ---

class MealPlanEntryOut(BaseModel):
    id: str
    date: date
    meal_type: str
    recipe_id: Optional[str]
    # recipe: Optional[RecipeOut] # Circular import risk, keep simple for MVP
    recipe_title: Optional[str] = None # Helper
    is_leftover: bool
    force_cook: bool = False
    method_choice: Optional[str]
    method_options_json: Optional[dict]
    
    class Config:
        from_attributes = True

class MealPlanOut(BaseModel):
    id: str
    week_start: date
    entries: List[MealPlanEntryOut]
    meta: Optional[dict] = None
    
    class Config:
        from_attributes = True

class PlanGenerateRequest(BaseModel):
    week_start: date

class EntryUpdate(BaseModel):
    recipe_id: Optional[str] = None
    is_leftover: Optional[bool] = None
    force_cook: Optional[bool] = None
    method_choice: Optional[str] = None


# --- Endpoints ---

@router.post("/plan/generate", response_model=MealPlanOut)
def generate_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Generate or regenerate a meal plan for the given week."""
    print(f"DEBUG: Generating plan for workspace {workspace.id} week_start={request.week_start}")
    plan = generate_week_plan(db, workspace.id, request.week_start)
    
    # Enrichment for response
    return enrich_plan_response(plan, db)


@router.get("/plan/current", response_model=MealPlanOut)
def get_current_plan(
    week_start: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Get the plan for the current week."""
    # Calculate Monday of current week if not provided
    if week_start is None:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
    else:
        monday = week_start

    print(f"DEBUG: Get current plan for workspace {workspace.id}. Target Week={monday}")
    
    plan = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace.id,
        MealPlan.week_start == monday
    ).order_by(MealPlan.id.desc()).first()
    
    if not plan:
        # Return empty structure or 404? 
        # Let's return 404 so UI knows to ask to generate
        raise HTTPException(status_code=404, detail="No plan found for this week")
        
    return enrich_plan_response(plan, db)


@router.patch("/plan/entries/{entry_id}", response_model=MealPlanEntryOut)
def update_entry(
    entry_id: str,
    update: EntryUpdate,
    db: Session = Depends(get_db)
):
    entry = db.query(MealPlanEntry).filter(MealPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Validation: Ensure recipe exists in workspace if changing
    if update.recipe_id is not None:
        # Get recipe (and verify workspace match - MVP assumes all valid recipes are in same workspace for now)
        # Ideally: get entry.meal_plan.workspace_id
        plan = db.query(MealPlan).filter(MealPlan.id == entry.meal_plan_id).first()
        workspace_id = plan.workspace_id
        
        recipe = db.query(Recipe).filter(
            Recipe.id == update.recipe_id, 
            Recipe.workspace_id == workspace_id
        ).first()
        
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found in workspace")
            
        entry.recipe_id = update.recipe_id
        
        # Re-compute method options
        # Ported logic from planner_agent (simplified)
        methods = {
            "Stove": {"time": f"{recipe.time_minutes}m", "effort": "Medium"},
            "Oven": {"time": f"{int(recipe.time_minutes or 15)*1.2}m", "effort": "Low"},
        }
        entry.method_options_json = methods
        
        # Reset method choice if not valid (or just default)
        is_leftover = update.is_leftover if update.is_leftover is not None else entry.is_leftover
        entry.method_choice = "Stove" if not is_leftover else "Microwave"

    if update.is_leftover is not None:
        entry.is_leftover = update.is_leftover
        # Update method choice based on leftover status if not set
        if not update.method_choice: # Only if user didn't explicitly set it
             entry.method_choice = "Microwave" if entry.is_leftover else "Stove"

    if update.force_cook is not None:
        entry.force_cook = update.force_cook

    if update.method_choice is not None:
        entry.method_choice = update.method_choice
        
    db.commit()
    db.refresh(entry)
    
    # Enrich single entry
    return enrich_entry(entry, db)

# --- Helpers ---

def enrich_plan_response(plan: MealPlan, db: Session) -> MealPlanOut:
    """Hydrate recipe titles manually to avoid complex Pydantic nesting for now."""
    entries_out = []
    for entry in plan.entries:
        entries_out.append(enrich_entry(entry, db))
    
    return MealPlanOut(
        id=plan.id,
        week_start=plan.week_start,
        entries=entries_out,
        meta=getattr(plan, "meta", None)
    )

def enrich_entry(entry: MealPlanEntry, db: Session) -> MealPlanEntryOut:
    title = None
    if entry.recipe_id:
        # Optimize: could allow eager loading in main query
        # But lazy for MVP is fine
        recipe = db.query(Recipe).filter(Recipe.id == entry.recipe_id).first()
        if recipe:
            title = recipe.title
            
    return MealPlanEntryOut(
        id=entry.id,
        date=entry.date,
        meal_type=entry.meal_type,
        recipe_id=entry.recipe_id,
        recipe_title=title,
        is_leftover=entry.is_leftover,
        force_cook=entry.force_cook,
        method_choice=entry.method_choice,
        method_options_json=entry.method_options_json
    )
