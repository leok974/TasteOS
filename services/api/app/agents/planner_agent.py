
import random
from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Recipe, MealPlan, MealPlanEntry, UserPrefs

def generate_week_plan(
    db: Session, 
    workspace_id: str, 
    week_start: date
) -> MealPlan:
    """Generate a meal plan for a specific week based on heuristics.
    
    Algorithm:
    1. Fetch user prefs (leftover intensity, equipment).
    2. Fetch available recipes (anchors vs quick).
    3. Slot Anchors for Dinners (Mon, Wed, Fri).
    4. Slot Leftovers for Lunches (Tue, Thu, Sat).
    5. Fill gaps with variety.
    """
    
    # 1. Get Prefs
    prefs = db.query(UserPrefs).filter(UserPrefs.workspace_id == workspace_id).first()
    intensity = prefs.leftover_intensity if prefs else "medium"
    # equipment = prefs.equipment_flags if prefs else {} # Todo: use equipment for method filtering
    
    # 2. Get Recipes
    # In a real app, we'd filter by 'tags' or 'rating'. For MVP, just get all.
    all_recipes = db.query(Recipe).filter(Recipe.workspace_id == workspace_id).all()
    
    if not all_recipes:
        # Fallback if no recipes (shouldn't happen with seed)
        return create_empty_plan(db, workspace_id, week_start)
        
    random.shuffle(all_recipes)
    anchors = all_recipes[:4]  # Top 3-4 as anchors
    pool = all_recipes[4:] + all_recipes # Allow repeats if low on recipes
    
    # 3. Create Plan Object
    # Check existing?
    existing = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace_id, 
        MealPlan.week_start == week_start
    ).first()
    
    if existing:
        # For MVP, we replace the entries, but keep the plan ID? 
        # Or just delete and recreate? Let's delete entries for simplicity.
        db.query(MealPlanEntry).filter(MealPlanEntry.meal_plan_id == existing.id).delete()
        plan = existing
    else:
        plan = MealPlan(workspace_id=workspace_id, week_start=week_start)
        db.add(plan)
        db.flush() # get ID
        
    entries: List[MealPlanEntry] = []
    
    # Days: 0=Mon, 6=Sun
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        
        # --- Dinner Logic ---
        # Anchor days: Mon(0), Wed(2), Fri(4), Sun(6)
        if day_offset in [0, 2, 4, 6] and anchors:
            # Pick next anchor
            recipe = anchors.pop(0) if anchors else random.choice(all_recipes)
            entries.append(create_entry(plan.id, current_date, "dinner", recipe=recipe))
            
            # Save for leftover next day lunch?
            if day_offset < 6: # Next day exists in this week
                next_day_lunch_needed = True # Simplified
                if next_day_lunch_needed:
                     # Add to a queue or just handle in next iteration?
                     # Let's handle explicit leftovers here strictly.
                     pass 
        else:
            # Gap filling dinner
            # Try to pick something different from yesterday's cuisine?
            recipe = random.choice(all_recipes)
            entries.append(create_entry(plan.id, current_date, "dinner", recipe=recipe))

    # --- Lunch Logic ---
    # Need to see if yesterday's dinner was "batchable" (for MVP assume all anchors are)
    
    # Re-loop to fill lunches now that we kind of know dinners? 
    # Actually simpler: 
    # Mon Lunch: Random/Quick
    # Tue Lunch: Leftover from Mon Dinner
    # Wed Lunch: Random/Quick
    # Thu Lunch: Leftover from Wed Dinner
    # Fri Lunch: Random/Quick
    # Sat Lunch: Leftover from Fri Dinner
    # Sun Lunch: Leftover from Sat Dinner or Special?
    
    # Let's map the specific schedule for MVP deterministic feel
    schedule = {
        0: {"lunch": "fresh", "dinner": "anchor"}, # Mon
        1: {"lunch": "leftover", "dinner": "gap"},   # Tue
        2: {"lunch": "fresh", "dinner": "anchor"}, # Wed
        3: {"lunch": "leftover", "dinner": "gap"},   # Thu
        4: {"lunch": "fresh", "dinner": "anchor"}, # Fri
        5: {"lunch": "leftover", "dinner": "gap"},   # Sat
        6: {"lunch": "leftover", "dinner": "anchor"},# Sun
    }
    
    # Reset anchors for strict scheduling
    random.shuffle(all_recipes)
    anchors_queue = list(all_recipes) # Copy
    
    # Clear entries and restart with strict schedule for clarity
    entries = []
    
    # Track what we had for dinner to make leftovers
    yesterdays_dinner: Optional[Recipe] = None
    
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        day_type = schedule[day_offset]
        
        # Dinner
        if day_type["dinner"] == "anchor":
            # Pick unique if possible
            if anchors_queue:
                dinner_recipe = anchors_queue.pop(0)
            else:
                dinner_recipe = random.choice(all_recipes)
        else:
            # Gap
            dinner_recipe = random.choice(all_recipes)
            
        entries.append(create_entry(plan.id, current_date, "dinner", recipe=dinner_recipe))
        
        # Lunch
        if day_type["lunch"] == "leftover" and yesterdays_dinner:
            # Create leftover entry
            entries.append(create_entry(plan.id, current_date, "lunch", recipe=yesterdays_dinner, is_leftover=True))
        else:
            # Fresh lunch
            lunch_recipe = random.choice(all_recipes)
            entries.append(create_entry(plan.id, current_date, "lunch", recipe=lunch_recipe))
            
        yesterdays_dinner = dinner_recipe

    db.add_all(entries)
    db.commit()
    db.refresh(plan)
    return plan

def create_entry(plan_id, date_obj, meal_type, recipe, is_leftover=False):
    # Mock method options
    methods = {
        "Stove": {"time": f"{recipe.time_minutes}m", "effort": "Medium"},
        "Oven": {"time": f"{int(recipe.time_minutes or 15)*1.2}m", "effort": "Low"},
    }
    
    return MealPlanEntry(
        meal_plan_id=plan_id,
        date=date_obj,
        meal_type=meal_type,
        recipe_id=recipe.id,
        is_leftover=is_leftover,
        method_choice="Stove" if not is_leftover else "Microwave",
        method_options_json=methods
    )

def create_empty_plan(db, workspace_id, week_start):
    plan = MealPlan(workspace_id=workspace_id, week_start=week_start)
    db.add(plan)
    db.commit()
    return plan
