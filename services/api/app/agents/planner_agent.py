
import random
from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Recipe, MealPlan, MealPlanEntry, UserPrefs, PantryItem

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
    
    # LOOP AUTOMATION V1: Boost recipes that use expiring pantry items
    today = date.today()
    expires_threshold = today + timedelta(days=7) 
    
    use_soon_items = db.query(PantryItem).filter(
        PantryItem.workspace_id == workspace_id,
        (
            ((PantryItem.expires_on != None) & (PantryItem.expires_on <= expires_threshold)) |
            ((PantryItem.use_soon_at != None) & (PantryItem.use_soon_at <= today))
        )
    ).all()

    random.shuffle(all_recipes)

    if use_soon_items:
        priority_ingredients = {item.name.lower() for item in use_soon_items}
        
        def score_recipe(r):
             score = 0
             if not r.ingredients: return 0
             for ing in r.ingredients:
                 ing_name = ing.name.lower()
                 if ing_name in priority_ingredients:
                     score += 10
                 elif any(p in ing_name for p in priority_ingredients):
                     score += 5
             return score
        
        all_recipes.sort(key=score_recipe, reverse=True)
    else:
        priority_ingredients = set()
        
    anchors = all_recipes[:4]  # Top recipes (prioritized) as anchors
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
        
    # --- Strict Schedule Logic ---
    schedule = {
        0: {"lunch": "fresh", "dinner": "anchor"}, # Mon
        1: {"lunch": "leftover", "dinner": "gap"},   # Tue
        2: {"lunch": "fresh", "dinner": "anchor"}, # Wed
        3: {"lunch": "leftover", "dinner": "gap"},   # Thu
        4: {"lunch": "fresh", "dinner": "anchor"}, # Fri
        5: {"lunch": "leftover", "dinner": "gap"},   # Sat
        6: {"lunch": "leftover", "dinner": "anchor"},# Sun
    }
    
    # Use the sorted all_recipes as the source queue
    # If we shuffled here, we'd lose the 'use soon' priority
    if not use_soon_items:
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
            # Gap - Pick something from the pool (can be random)
            # If we want to maintain high urgency usage, we should pick from top too?
            # Let's pick random from top 50%? or just random.
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
    
    # Meta Calculation for Use Soon
    used_use_soon = set()
    print(f"DEBUG_PLANNER: use_soon_items count: {len(use_soon_items)}")
    if use_soon_items:
        # Scan entries for used priority ingredients
        # ... logic ...
        pass
        
        # Re-fetch or inspect used recipe IDs
        used_rids = {e.recipe_id for e in entries if e.recipe_id}
        # Get recipes (we have them in all_recipes memory, but easier to just check against priority)
        # We can scan all_recipes where id in used_rids
        
        used_recipes = [r for r in all_recipes if r.id in used_rids]
        
        for r in used_recipes:
             for ing in r.ingredients:
                 ing_name = ing.name.lower()
                 if ing_name in priority_ingredients:
                     used_use_soon.add(ing_name)
                 else:
                     # Check substring match
                     for p in priority_ingredients:
                         if p in ing_name:
                             used_use_soon.add(p)
    
    print(f"DEBUG_PLANNER: used_use_soon: {used_use_soon}")
    plan.meta = {
        "use_soon_used": list(used_use_soon),
        "boost_applied": bool(use_soon_items)
    }
    print(f"DEBUG_PLANNER: plan.meta attached: {plan.meta}")

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
