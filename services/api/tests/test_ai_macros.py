from app.models import Recipe, RecipeIngredient

def test_macro_analysis_mock(client, workspace, db_session):
    # 1. Create a recipe
    recipe = Recipe(workspace_id=workspace.id, title="Steak and Eggs", steps=[])
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    ing1 = RecipeIngredient(recipe_id=recipe.id, name="Steak", qty=1, unit="lb")
    ing2 = RecipeIngredient(recipe_id=recipe.id, name="Eggs", qty=2, unit="pcs")
    db_session.add_all([ing1, ing2])
    db_session.commit()
    
    # 2. Call Macros endpoint
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/ai/macros",
        json={"recipe_id": recipe.id},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    # New enhanced response structure
    assert "calories_range" in data
    assert "min" in data["calories_range"]
    assert "max" in data["calories_range"]
    assert "confidence" in data
    assert "disclaimer" in data
    assert "tags" in data

def test_macro_analysis_not_found(client, workspace):
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/ai/macros",
        json={"recipe_id": "non-existent"},
        headers=headers
    )
    assert response.status_code == 404
