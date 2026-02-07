import pytest
import uuid
from app.models import Recipe

def test_recipe_tips_lifecycle(client, workspace, db_session):
    # 1. Setup Recipe
    recipe = Recipe(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id, 
        title="Test Pasta Carbonara", 
        servings=2, 
        time_minutes=15
    )
    db_session.add(recipe)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 2. Call Tips (Storage)
    # Tests run in MOCK mode usually.
    response = client.post(
        "/api/ai/recipe_tips",
        json={"recipe_id": recipe.id, "scope": "storage"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "tips" in data
    assert len(data["tips"]) > 0
    # In mock mode, we expect source="mock" (or heuristic)
    # Checking content from heuristic fallback
    assert any("airtight" in t.lower() for t in data["tips"])

    # 3. Call Tips (Reheat)
    response_rh = client.post(
        "/api/ai/recipe_tips",
        json={"recipe_id": recipe.id, "scope": "reheat"},
        headers=headers
    )
    assert response_rh.status_code == 200
    data_rh = response_rh.json()
    assert any("reheat" in t.lower() for t in data_rh["tips"])

def test_recipe_tips_404(client, workspace):
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/ai/recipe_tips",
        json={"recipe_id": str(uuid.uuid4()), "scope": "storage"},
        headers=headers
    )
    assert response.status_code == 404
