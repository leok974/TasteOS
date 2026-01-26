import pytest
import uuid
from datetime import date
from decimal import Decimal
from app.models import Recipe, RecipeIngredient, MealPlan, MealPlanEntry, CookSession, Leftover, PantryItem, PantryTransaction
from sqlalchemy import select

def test_auto_leftover_on_complete(client, workspace, db_session):
    # 1. Setup Data
    # Recipe
    recipe = Recipe(workspace_id=workspace.id, title="Test Curry", steps=[])
    db_session.add(recipe)
    db_session.commit()
    
    # Meal Plan Entry (Today)
    mp = MealPlan(
        workspace_id=workspace.id,
        week_start=date.today(), # simplistic
        settings_json={}
    )
    db_session.add(mp)
    db_session.commit()
    
    entry = MealPlanEntry(
        meal_plan_id=mp.id,
        date=date.today(),
        meal_type="dinner",
        recipe_id=recipe.id
    )
    db_session.add(entry)
    db_session.commit()
    
    # 2. Start Session
    # Using direct DB creation to speed up
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    # 3. Complete Session via API
    headers = {"X-Workspace-Id": workspace.id}
    res = client.patch(f"/api/cook/session/{session.id}/end?action=complete", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    
    # 4. Verify Leftovers Created
    leftover = db_session.scalar(
        select(Leftover).where(
            Leftover.plan_entry_id == entry.id
        )
    )
    assert leftover is not None
    assert leftover.name == "Test Curry"
    assert leftover.pantry_item_id is not None
    
    # 5. Verify Pantry Item
    p_item = db_session.scalar(
        select(PantryItem).where(PantryItem.id == leftover.pantry_item_id)
    )
    assert p_item is not None
    assert p_item.category == "Leftovers"
    assert p_item.source == "leftover"

def test_auto_leftover_dedupe(client, workspace, db_session):
    """Completing twice shouldn't create duplicates."""
    # Setup
    recipe = Recipe(workspace_id=workspace.id, title="Test Curry", steps=[])
    db_session.add(recipe)
    mp = MealPlan(workspace_id=workspace.id, week_start=date.today(), settings_json={})
    db_session.add(mp)
    db_session.commit()
    entry = MealPlanEntry(meal_plan_id=mp.id, date=date.today(), meal_type="dinner", recipe_id=recipe.id)
    db_session.add(entry)
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()

    headers = {"X-Workspace-Id": workspace.id}
    
    # First Complete
    client.patch(f"/api/cook/session/{session.id}/end?action=complete", headers=headers)
    
    # Count leftovers
    count1 = db_session.query(Leftover).count()
    
    # Second Complete
    client.patch(f"/api/cook/session/{session.id}/end?action=complete", headers=headers)
    
    count2 = db_session.query(Leftover).count()
    assert count1 == count2
    
def test_pantry_decrement_flow(client, workspace, db_session):
    # 1. Setup
    # Pantry Item
    p_rice = PantryItem(workspace_id=workspace.id, name="Basmati Rice", qty=10.0, unit="cups")
    db_session.add(p_rice)
    
    # Recipe
    recipe = Recipe(workspace_id=workspace.id, title="Rice Dish", servings=4)
    db_session.add(recipe)
    db_session.commit()
    
    # Ingredient
    ing = RecipeIngredient(recipe_id=recipe.id, name="Basmati Rice", qty=2.0, unit="cups")
    db_session.add(ing)
    db_session.commit()
    
    # Session (make 2 servings -> expect 1 cup usage)
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active", servings_target=2)
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-Id": workspace.id}
    
    # 2. Preview
    res = client.post(f"/api/cook/session/{session.id}/pantry/decrement/preview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["pantry_item_id"] == p_rice.id
    assert item["qty_needed"] == 1.0 # 2 * (2/4)
    
    # 3. Apply
    res = client.post(f"/api/cook/session/{session.id}/pantry/decrement/apply", headers=headers, json={"force": False})
    assert res.status_code == 200
    
    # Check DB
    db_session.refresh(p_rice)
    assert float(p_rice.qty) == 9.0
    
    txn = db_session.scalar(select(PantryTransaction).where(PantryTransaction.ref_id == session.id))
    assert txn is not None
    assert float(txn.delta_qty) == -1.0
    
    # 4. Undo
    res = client.post(f"/api/cook/session/{session.id}/pantry/decrement/undo", headers=headers)
    assert res.status_code == 200
    
    db_session.refresh(p_rice)
    db_session.refresh(txn)
    assert float(p_rice.qty) == 10.0
    assert txn.undone_at is not None

from unittest.mock import patch

def test_grocery_respects_leftovers(client, workspace, db_session):
    # 1. Setup Recipes
    r_cook = Recipe(workspace_id=workspace.id, title="Fresh Meal", steps=[])
    r_leftover_plan = Recipe(workspace_id=workspace.id, title="Leftover Lunch", steps=[])
    r_active_leftover = Recipe(workspace_id=workspace.id, title="Existing Leftover", steps=[])
    db_session.add_all([r_cook, r_leftover_plan, r_active_leftover])
    db_session.commit()
    
    # 2. Setup Active Leftover
    lo = Leftover(
        workspace_id=workspace.id,
        recipe_id=r_active_leftover.id,
        name="Existing LO",
        servings_left=2
    )
    db_session.add(lo)
    db_session.commit()
    
    # 3. Setup Plan
    mp = MealPlan(workspace_id=workspace.id, week_start=date.today(), settings_json={})
    db_session.add(mp)
    db_session.commit()
    
    # Entry 1: To Cook (Should include)
    e1 = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_cook.id, date=date.today(), meal_type="dinner")
    # Entry 2: Planned Leftover (Should exclude)
    e2 = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_leftover_plan.id, is_leftover=True, date=date.today(), meal_type="lunch")
    # Entry 3: To Cook but Active Leftover Exists (Should exclude)
    e3 = MealPlanEntry(meal_plan_id=mp.id, recipe_id=r_active_leftover.id, date=date.today(), meal_type="dinner")
    
    db_session.add_all([e1, e2, e3])
    db_session.commit()
    
    # 4. Mock Agent and Call
    with patch("app.routers.grocery.generate_grocery_list") as mock_gen:
        mock_gen.return_value.id = str(uuid.uuid4())
        mock_gen.return_value.items = []
        mock_gen.return_value.markdown = "Test List"
        mock_gen.return_value.created_at = date.today()
        mock_gen.return_value.source = "mock-source"
        
        resp = client.post(f"/api/grocery/generate", json={"plan_id": mp.id, "recipe_ids": []})
        assert resp.status_code == 200
        
        kwargs = mock_gen.call_args.kwargs
        passed_ids = kwargs['recipe_ids']
        
        assert r_cook.id in passed_ids, "Fresh meal should be in grocery list"
        assert r_leftover_plan.id not in passed_ids, "Plan entry marked is_leftover should be skipped"
        assert r_active_leftover.id not in passed_ids, "Recipe with active leftovers should be skipped"
