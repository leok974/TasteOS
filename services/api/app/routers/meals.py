from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import List, Optional

from ..db import get_db
from ..models import MealLog, Recipe
from ..schemas import MealLogCreate, MealLogRead, DailyNutritionSummary
from ..services.nutrition_service import calculate_macros_for_log

router = APIRouter(prefix="/meals", tags=["Meals & Nutrition"])


@router.post("/log", response_model=MealLogRead)
def log_meal(
    payload: MealLogCreate, 
    db: Session = Depends(get_db),
    x_workspace_id: str = Header(..., alias="X-Workspace-Id")
):
    # 1. Fetch the recipe to get current macros
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 2. Generate the snapshot
    # Assuming recipe.macros is a JSON/Dict field in your Recipe model
    snapshot = calculate_macros_for_log(recipe.macros or {}, payload.servings)

    # 3. Persist the log
    new_log = MealLog(
        recipe_id=payload.recipe_id,
        workspace_id=x_workspace_id,
        timestamp=payload.timestamp,
        servings=payload.servings,
        notes=payload.notes,
        macros_snapshot=snapshot
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


@router.get("/summary", response_model=DailyNutritionSummary)
def get_daily_summary(
    target_date: date, 
    db: Session = Depends(get_db),
    x_workspace_id: str = Header(..., alias="X-Workspace-Id")
):
    # Filter logs by workspace and specific date
    logs = db.query(MealLog).filter(
        MealLog.workspace_id == x_workspace_id,
        func.date(MealLog.timestamp) == target_date
    ).all()

    totals = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
    
    for log in logs:
        snapshot = log.macros_snapshot or {}
        for key in totals:
            totals[key] += snapshot.get(key, 0)

    return {
        "date": target_date.isoformat(),
        "totals": totals,
        "logs": logs
    }
