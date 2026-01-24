from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import get_db
from app.deps import get_workspace
from app.models import Workspace, PantryItem
from app.services.ai_service import ai_service, SubstitutionSuggestion

router = APIRouter(prefix="/ai", tags=["ai"])

class SubstituteRequest(BaseModel):
    ingredient: str
    context: Optional[str] = None

@router.post("/substitute", response_model=SubstitutionSuggestion)
def suggest_substitute(
    payload: SubstituteRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """
    Suggest a substitute for an ingredient based on available pantry items.
    """
    # 1. Fetch pantry items
    stmt = select(PantryItem.name).where(PantryItem.workspace_id == workspace.id)
    pantry_items = db.execute(stmt).scalars().all()
    pantry_list = list(pantry_items)

    # 2. Call AI Service
    suggestion = ai_service.suggest_substitute(
        ingredient=payload.ingredient,
        pantry_items=pantry_list, 
        context=payload.context or ""
    )
    
    return suggestion

class MacroRequest(BaseModel):
    recipe_id: str

@router.post("/macros")
def analyze_macros(
    payload: MacroRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    from app.models import Recipe
    # Fetch recipe
    recipe = db.scalar(select(Recipe).where(Recipe.id == payload.recipe_id))
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ing_names = [i.name for i in recipe.ingredients]
    result = ai_service.summarize_macros(recipe.title, ing_names)
    return result

