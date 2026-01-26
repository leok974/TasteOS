import pytest
import uuid
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from app.models import Recipe, RecipeIngredient, MealPlan, MealPlanEntry, Leftover

def test_overrides_and_meta(client, workspace, db_session):
    # 1. Setup Recipes
    r_todo = Recipe(workspace_id=workspace.id, title="Classic Dish", servings=4, 
                    ingredients=[RecipeIngredient(name="Beef", qty=1, unit="kg")])
    r_planned_lo = Recipe(workspace_id=workspace.id, title="Leftover Lunch", servings=4)
    r_active_lo = Recipe(workspace_id=workspace.id, title="Lasagna", servings=4,
                         ingredients=[RecipeIngredient(name="Pasta", qty=500, unit="g")])
    r_partial = Recipe(workspace_id=workspace.id, title="Chili", servings=4,
                       ingredients=[RecipeIngredient(name="Beans", qty=400, unit="g")])
                       
    db_session.add_all([r_todo, r_planned_lo, r_active_lo, r_partial])
    db_session.commit()

    # 2. Setup Active Leftovers
    # Full coverage for Lasagna (4 servings left vs 4 planned)
    lo_full = Leftover(workspace_id=workspace.id, recipe_id=r_active_lo.id, name="Lasagna LO", servings_left=4)
    # Partial coverage for Chili (2 servings left vs 4 planned -> 0.5 factor)
    lo_partial = Leftover(workspace_id=workspace.id, recipe_id=r_partial.id, name="Chili LO", servings_left=2)
    
    db_session.add_all([lo_full, lo_partial])
    db_session.commit()

    # 3. Setup Meal Plan
    mp = MealPlan(workspace_id=workspace.id, week_start=date.today(), settings_json={})
    db_session.add(mp)
    db_session.commit()
    
    # Entries
    # 1. Planned leftover (explicit) -> Should Skip
    e_planned_lo = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_planned_lo.id, date=date.today(), meal_type="lunch", is_leftover=True)
    
    # 2. Active leftover (full) -> Should Skip
    e_active_lo = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_active_lo.id, date=date.today(), meal_type="dinner")
    
    # 3. Partial leftover -> Should Include but Reduce
    e_partial = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_partial.id, date=date.today(), meal_type="dinner")
    
    # 4. Forced cook (simulating manual override on active leftover)
    # We'll use a new recipe for this to verify force_cook
    r_forced = Recipe(workspace_id=workspace.id, title="Forced Meal", servings=4)
    # Leftover exists but entry is forced
    lo_forced = Leftover(workspace_id=workspace.id, recipe_id=r_forced.id, name="Forced LO", servings_left=4)
    db_session.add_all([r_forced, lo_forced])
    db_session.commit()
    
    e_forced = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_forced.id, date=date.today(), meal_type="dinner", force_cook=True)
    
    db_session.add_all([e_planned_lo, e_active_lo, e_partial, e_forced])
    db_session.commit()

    # Mock agent to prevent actual DB writes for grocery list and inspect inputs
    with patch("app.routers.grocery.generate_grocery_list") as mock_gen:
        # Setup mock return
        mock_gen.return_value.id = str(uuid.uuid4())
        mock_gen.return_value.items = []
        mock_gen.return_value.source = "test"
        mock_gen.return_value.created_at = date.today()
        
        # --- Test 1: Default Generation with Meta ---
        resp = client.post("/api/grocery/generate", json={"plan_id": mp.id})
        assert resp.status_code == 200
        data = resp.json()
        meta = data["meta"]
        
        # Check Agent Inputs
        # recipe_scaling passed?
        kwargs = mock_gen.call_args.kwargs
        scaling = kwargs["recipe_scaling"]
        r_ids = kwargs["recipe_ids"]
        
        # Verify skips
        assert r_planned_lo.id not in r_ids
        assert r_active_lo.id not in r_ids
        assert r_partial.id in r_ids
        assert r_forced.id in r_ids
        
        # Verify Scaling
        assert scaling[r_partial.id] == 0.5
        
        # Verify Meta Response
        assert meta["skipped_count"] == 2 # Planned LO + Active LO
        assert meta["included_count"] == 2 # Partial + Forced
        
        reasons = {item["recipe_id"]: item["reason"] for item in meta["skipped_entries"]}
        assert reasons[r_planned_lo.id] == "entry_marked_leftover"
        assert reasons[r_active_lo.id] == "active_leftover_exists"
        
        reduced_map = {item["recipe_id"]: item["factor"] for item in meta["reduced_recipes"]}
        assert reduced_map[r_partial.id] == 0.5

    # --- Test 2: Override via include_entry_ids ---
    with patch("app.routers.grocery.generate_grocery_list") as mock_gen:
        mock_gen.return_value.id = "mock"
        mock_gen.return_value.items = []
        mock_gen.return_value.source = "test"
        mock_gen.return_value.created_at = date.today()
        
        resp2 = client.post("/api/grocery/generate", json={
            "plan_id": mp.id, 
            "include_entry_ids": [e_active_lo.id]
        })
        meta2 = resp2.json()["meta"]
        
        # Active LO should now be included
        skipped_ids = [item["recipe_id"] for item in meta2["skipped_entries"]]
        assert r_active_lo.id not in skipped_ids
        
        # Call args check
        r_ids = mock_gen.call_args.kwargs["recipe_ids"]
        assert r_active_lo.id in r_ids

    # --- Test 3: Override via ignore_leftovers ---
    with patch("app.routers.grocery.generate_grocery_list") as mock_gen:
        mock_gen.return_value.id = "mock"
        mock_gen.return_value.items = []
        mock_gen.return_value.source = "test"
        mock_gen.return_value.created_at = date.today()

        resp3 = client.post("/api/grocery/generate", json={
            "plan_id": mp.id,
            "ignore_leftovers": True
        })
        meta3 = resp3.json()["meta"]
        
        skipped_ids = [item["recipe_id"] for item in meta3["skipped_entries"]]
        
        # Active LO should be included because we ignore leftovers in fridge
        assert r_active_lo.id not in skipped_ids 
        assert r_active_lo.id in mock_gen.call_args.kwargs["recipe_ids"]
        
        # Planned LO should STILL be skipped because it is explicit in plan (unless we include_ids)
        assert r_planned_lo.id in skipped_ids
        assert r_planned_lo.id not in mock_gen.call_args.kwargs["recipe_ids"]
