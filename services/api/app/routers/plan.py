
from datetime import date, timedelta, datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models import MealPlan, MealPlanEntry, Recipe, Workspace
from ..agents.planner_agent import generate_week_plan
from ..deps import get_workspace
from ..services.autofill import generate_use_soon_proposals, apply_proposals

router = APIRouter()

# --- Schemas ---

class MealPlanEntryOut(BaseModel):
    id: str
    date: date
    meal_type: str
    recipe_id: Optional[str]
    # recipe: Optional[RecipeOut] # Circular import risk, keep simple for MVP
    recipe_title: Optional[str] = None # Helper
    recipe_total_minutes: Optional[int] = None
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

class PlanEntryCreate(BaseModel):
    date: date
    meal: str  # lunch | dinner
    recipe_id: str
    servings_override: Optional[int] = None


# --- Autofill Schemas ---

class AutofillRequest(BaseModel):
    days: int = 5
    max_swaps: int = 3
    slots: List[str] = ["dinner"]
    ignore_entry_ids: List[str] = []
    prefer_quick: bool = True
    strict_variety: bool = False # If True, disallow any duplicates in the week
    max_duplicates_per_recipe: int = 2

class AutofillProposal(BaseModel):
    proposal_id: str
    plan_entry_id: str
    date: date
    meal: str
    before: Optional[Dict[str, Any]]
    after: Dict[str, Any]
    score: float
    reasons: List[Dict[str, Any]]
    constraints: Dict[str, bool]

class AutofillResponse(BaseModel):
    week_start: date
    meta: Dict[str, Any]
    proposals: List[AutofillProposal]

class ApplyChange(BaseModel):
    plan_entry_id: str
    recipe_id: str

class ApplyRequest(BaseModel):
    week_start: date
    changes: List[ApplyChange]

class ApplyResponse(BaseModel):
    applied: int
    plan: MealPlanOut
    meta: Dict[str, Any]

# --- Endpoints ---

@router.post("/autofill/use-soon", response_model=AutofillResponse)
def get_autofill_proposals(
    request: AutofillRequest, # Optional body
    week_start: date = Query(..., description="Start date of the week (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Generate proposals to swap existing plan entries with use-soon items."""
    result = generate_use_soon_proposals(
        db,
        workspace.id,
        week_start,
        days=request.days,
        max_swaps=request.max_swaps,
        ignore_entry_ids=request.ignore_entry_ids,
        slots=request.slots,
        prefer_quick=request.prefer_quick,
        strict_variety=request.strict_variety,
        max_duplicates_per_recipe=request.max_duplicates_per_recipe
    )
    return result

@router.post("/autofill/use-soon/apply", response_model=ApplyResponse)
def apply_autofill_proposals(
    request: ApplyRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"), 
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Apply approved proposals to the plan."""
    # TODO: Implement actual idempotency with Redis using idempotency_key
    # For MVP, we just proceed.
    
    # 1. Apply changes
    changes_list = [{"plan_entry_id": c.plan_entry_id, "recipe_id": c.recipe_id} for c in request.changes]
    count = apply_proposals(db, workspace.id, changes_list)
    
    # 2. Re-fetch plan
    plan = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace.id,
        MealPlan.week_start == request.week_start
    ).first()
    
    if not plan:
        # Should imply plan created? If not found after apply, something oddly wrong
        raise HTTPException(status_code=404, detail="Plan not found after update")

    return {
        "applied": count,
        "plan": enrich_plan_response(plan, db),
        "meta": {"idempotent_replay": False}
    }


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


@router.get("/plan/current", response_model=Optional[MealPlanOut])
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

    # print(f"DEBUG: Get current plan for workspace {workspace.id}. Target Week={monday}")
    
    plan = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace.id,
        MealPlan.week_start == monday
    ).order_by(MealPlan.id.desc()).first()
    
    if not plan:
        # Return none to indicate no plan (avoiding 404 errors in console)
        return None
        
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
        minutes = recipe.total_minutes or recipe.time_minutes
        stove_str = f"{minutes}m" if minutes else None
        oven_base = minutes if minutes else 15
        
        methods = {
            "Stove": {"time": stove_str, "effort": "Medium"},
            "Oven": {"time": f"{int(oven_base * 1.2)}m", "effort": "Low"},
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


@router.post("/plan/entries", response_model=MealPlanEntryOut)
def create_plan_entry(
    entry_in: PlanEntryCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Add a recipe to the meal plan (upsert logic)."""
    
    # 1. Determine Week Start (Monday)
    monday = entry_in.date - timedelta(days=entry_in.date.weekday())
    
    # 2. Get or Create Plan
    plan = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace.id,
        MealPlan.week_start == monday
    ).first()
    
    if not plan:
        plan = MealPlan(
            workspace_id=workspace.id,
            week_start=monday,
            settings_json={} 
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

    # 3. Check Recipe Exists
    recipe = db.query(Recipe).filter(
        Recipe.id == entry_in.recipe_id,
        Recipe.workspace_id == workspace.id
    ).first()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 4. Upsert Entry
    # Check if slot occupied
    existing_entry = db.query(MealPlanEntry).filter(
        MealPlanEntry.meal_plan_id == plan.id,
        MealPlanEntry.date == entry_in.date,
        MealPlanEntry.meal_type == entry_in.meal
    ).first()

    if existing_entry:
        # Update existing
        existing_entry.recipe_id = entry_in.recipe_id
        existing_entry.is_leftover = False
        existing_entry.method_choice = "Stove" # Reset default
        # Note: servings_override not persisted yet
        db_entry = existing_entry
    else:
        # Create new
        db_entry = MealPlanEntry(
            meal_plan_id=plan.id,
            date=entry_in.date,
            meal_type=entry_in.meal,
            recipe_id=entry_in.recipe_id,
            is_leftover=False,
            # servings_override skipped
        )
        db.add(db_entry)
    
    # Helper to generate method options (simplified version of update_entry logic)
    minutes = recipe.total_minutes or recipe.time_minutes
    stove_str = f"{minutes}m" if minutes else None
    oven_base = minutes if minutes else 15
    methods = {
         "Stove": {"time": stove_str, "effort": "Medium"},
         "Oven": {"time": f"{min(999, int(oven_base * 1.2))}m", "effort": "Low"}, 
    }
    db_entry.method_options_json = methods
    db_entry.method_choice = "Stove"

    db.commit()
    db.refresh(db_entry)
    
    return enrich_entry(db_entry, db)


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
    total_minutes = None
    if entry.recipe_id:
        # Optimize: could allow eager loading in main query
        # But lazy for MVP is fine
        recipe = db.query(Recipe).filter(Recipe.id == entry.recipe_id).first()
        if recipe:
            title = recipe.title
            total_minutes = recipe.total_minutes or recipe.time_minutes
            
    return MealPlanEntryOut(
        id=entry.id,
        date=entry.date,
        meal_type=entry.meal_type,
        recipe_id=entry.recipe_id,
        recipe_title=title,
        recipe_total_minutes=total_minutes,
        is_leftover=entry.is_leftover,
        force_cook=entry.force_cook,
        method_choice=entry.method_choice,
        method_options_json=entry.method_options_json
    )
