import sys
import os

# Add the app directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import SessionLocal
from app import models
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc
import datetime

db_maker = SessionLocal()
db = db_maker()
try:
    # Get the most recent meal plan
    stmt = select(models.MealPlan).order_by(desc(models.MealPlan.week_start)).limit(1).options(
        selectinload(models.MealPlan.entries).selectinload(models.MealPlanEntry.recipe).selectinload(models.Recipe.ingredients)
    )
    plan = db.execute(stmt).scalar_one_or_none()
    
    if plan:
        print(f"DEBUG_PLAN_ID: {plan.id}")
        print(f"DEBUG_WEEK_START: {plan.week_start}")
        print(f"DEBUG_ENTRIES_COUNT: {len(plan.entries)}")
        for entry in plan.entries:
            r = entry.recipe
            if r:
                print(f" - Entry: {entry.date} ({entry.meal_type}) -> Recipe: {r.title} (ID: {r.id})")
                print(f"   Ingredients Count: {len(r.ingredients)}")
                for ing in r.ingredients:
                     print(f"    * {ing.name} ({ing.qty} {ing.unit})")
            else:
                print(f" - Entry: {entry.date} ({entry.meal_type}) -> NO RECIPE LINKED")
    else:
        print("DEBUG_NO_PLAN_FOUND")
finally:
    db.close()
