import pytest
from app.models import Recipe, RecipeStep, RecipeImage
from unittest.mock import patch, MagicMock

def test_delete_recipe_e2e(client, db_session, workspace):
    # 1. Setup Data
    # Create recipe with steps and images to verify cascade delete and file cleanup
    recipe = Recipe(
        title="To Be Deleted",
        workspace_id=workspace.id,
        steps=[RecipeStep(title="Step 1", step_index=0)],
        images=[
            RecipeImage(
                status="ready", 
                storage_key="recipes/123/img.jpg", 
                provider="local",
                model="test",
                prompt="test"
            )
        ]
    )
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    recipe_id = recipe.id
    # Access relationships before session might be closed/expired, though 'refresh' helps.
    step_id = recipe.steps[0].id
    image_id = recipe.images[0].id

    # 2. Mock Storage
    # We patch the storage object imported in app.routers.recipes
    with patch("app.routers.recipes.storage") as mock_storage:
        
        # 3. Call Delete Endpoint
        headers = {"X-Workspace-Id": workspace.id}
        response = client.delete(f"/api/recipes/{recipe_id}", headers=headers)
        
        # 4. Assertions
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        # Verify DB deletion
        # Using a fresh session view
        db_session.expire_all()
        assert db_session.query(Recipe).filter_by(id=recipe_id).first() is None
        assert db_session.query(RecipeStep).filter_by(id=step_id).first() is None
        assert db_session.query(RecipeImage).filter_by(id=image_id).first() is None
        
        # Verify Storage deletion
        mock_storage.delete.assert_called_with("recipes/123/img.jpg")

def test_delete_recipe_not_found(client, workspace):
    response = client.delete("/api/recipes/nonexistent-id", headers={"X-Workspace-Id": workspace.id})
    assert response.status_code == 404
