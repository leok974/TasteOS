
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Recipe, PantryItem, RecipeIngredient, RecipeStep
from app.main import app

def test_plan_generation_boosts_use_soon(client: TestClient, db_session: Session):
    # Setup Workspace
    response = client.post("/api/workspaces/", json={"name": "Plan Boost Test"})
    ws_id = response.json()["id"]
    headers = {"X-Workspace-ID": ws_id}
    
    # Setup Recipes
    # 1. Spinach Salad (Uses Spinach)
    r1 = Recipe(
        workspace_id=ws_id,
        title="Spinach Salad",
        steps=[RecipeStep(step_index=0, title="Mix")],
        servings=2
    )
    r1.ingredients = [
        RecipeIngredient(name="Spinach", qty=200, unit="g"),
        RecipeIngredient(name="Dressing", qty=1, unit="tsp")
    ]
    
    # 2. Burger (No Spinach)
    r2 = Recipe(
        workspace_id=ws_id,
        title="Classic Burger",
        steps=[RecipeStep(step_index=0, title="Grill")],
        servings=2
    )
    r2.ingredients = [RecipeIngredient(name="Beef", qty=200, unit="g")]
    
    # 3. Pasta (No Spinach)
    r3 = Recipe(
         workspace_id=ws_id,
         title="Pasta",
         steps=[],
         servings=2
    )
    r3.ingredients = [RecipeIngredient(name="Noodles", qty=100, unit="g")]

    # 4. Tacos (No Spinach)
    r4 = Recipe(
         workspace_id=ws_id,
         title="Tacos",
         steps=[],
         servings=2
    )
    r4.ingredients = [RecipeIngredient(name="Shells", qty=3, unit="pcs")]
    
    db_session.add_all([r1, r2, r3, r4])
    db_session.commit()
    
    # Setup Pantry: Spinach expires tomorrow
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    client.post("/api/pantry/", json={
        "name": "Spinach",
        "expires_on": tomorrow.isoformat()
    }, headers=headers)
    
    # Generate Plan
    p_resp = client.post("/api/plan/generate", json={
        "week_start": today.isoformat()
    }, headers=headers)
    
    assert p_resp.status_code == 200
    plan = p_resp.json()
    
    # Verify Meta
    print("Plan Meta:", plan.get("meta"))
    assert plan["meta"]["boost_applied"] is True
    assert "spinach" in plan["meta"]["use_soon_used"]
    
    # Verify Spinach Salad is likely in the plan (first anchor?)
    # Since we only have 4 recipes, all will be used, but Spinach Salad should likely be early or an anchor.
    # Anchors are index 0, 2, 4, 6 (Dinner).
    entries = plan["entries"]
    
    # Check if Spinach Salad is present
    spinach_entries = [e for e in entries if e["recipe_title"] == "Spinach Salad"]
    assert len(spinach_entries) > 0
    
    # Check if Beef is NOT in meta used_use_soon
    assert "beef" not in plan["meta"]["use_soon_used"]

