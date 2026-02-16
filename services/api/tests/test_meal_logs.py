import pytest
from datetime import datetime, date
from app.models import Recipe, MealLog

@pytest.fixture
def test_recipe(db_session, workspace):
    recipe = Recipe(
        workspace_id=workspace.id,
        title="Test Macro Recipe",
        servings=2,
        macros={"calories": 500, "protein_g": 30, "carbs_g": 40, "fat_g": 10}
    )
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    return recipe

def test_meal_log_snapshot_integrity(client, test_recipe, db_session, workspace):
    # 1. Log a meal with 1.5 servings
    payload = {
        "recipe_id": test_recipe.id,
        "timestamp": datetime.now().isoformat(),
        "servings": 1.5,
        "notes": "Testing snapshot"
    }
    headers = {"X-Workspace-Id": workspace.id}
    
    response = client.post("/api/meals/log", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    log_id = data["id"]
    
    # Verify calculation: 500 * 1.5 = 750
    assert data["macros_snapshot"]["calories"] == 750.0
    
    # 2. Update the recipe's original macros in the DB
    test_recipe.macros = {"calories": 9999, "protein_g": 0}
    db_session.add(test_recipe)
    db_session.commit()
    
    # 3. Fetch the meal log via API or DB and ensure snapshot is preserved
    # Fetch summary for today
    today = date.today().isoformat()
    summary_res = client.get(f"/api/meals/summary?target_date={today}", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    
    log_entry = next(l for l in summary["logs"] if l["id"] == log_id)
    assert log_entry["macros_snapshot"]["calories"] == 750.0
    assert log_entry["macros_snapshot"]["protein_g"] == 45.0 # 30 * 1.5

def test_workspace_isolation(client, test_recipe, db_session, workspace):
    # Create another workspace
    from app.models import Workspace
    ws2 = Workspace(id="11111111-1111-1111-1111-111111111111", slug="ws2", name="Workspace 2")
    db_session.add(ws2)
    db_session.commit()
    
    # 1. Log meal in Workspace A (already done or do new one)
    payload = {
        "recipe_id": test_recipe.id,
        "timestamp": datetime.now().isoformat(),
        "servings": 1.0
    }
    client.post("/api/meals/log", json=payload, headers={"X-Workspace-Id": workspace.id})
    
    # 2. Query summary for Workspace B
    today = date.today().isoformat()
    res = client.get(f"/api/meals/summary?target_date={today}", headers={"X-Workspace-Id": ws2.id})
    assert res.status_code == 200
    data = res.json()
    
    # 3. Assert Workspace B summary is empty/zeros
    assert data["totals"]["calories"] == 0
    assert len(data["logs"]) == 0
