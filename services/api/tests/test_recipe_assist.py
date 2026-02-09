import pytest
from app.models import Recipe
from app.settings import settings

@pytest.fixture
def recipe_for_assist(db_session, workspace):
    r = Recipe(
        workspace_id=workspace.id,
        title="Assist Cake",
        steps=[],
        ingredients=[]
    )
    db_session.add(r)
    db_session.commit()
    return r

def test_assist_mock_mode(client, recipe_for_assist, workspace):
    print("Testing assist in mock mode...")
    
    # Force mock mode
    original_mode = settings.ai_mode
    settings.ai_mode = "mock"
    
    try:
        response = client.post(
            f"/api/recipes/{recipe_for_assist.id}/assist",
            json={
                "messages": [{"role": "user", "content": "How do I bake this?"}]
            },
            headers={"X-Workspace-Id": workspace.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify schema match
        assert "reply" in data
        assert "used_ai" in data
        assert "suggested" in data
        
        assert data["used_ai"] is False
        assert "Mock" in data["reply"] or "mock" in data["reply"].lower()
        
    finally:
        settings.ai_mode = original_mode

def test_assist_404(client, workspace):
    response = client.post(
        f"/api/recipes/invalid-id/assist",
        json={"messages": []},
        headers={"X-Workspace-Id": workspace.id}
    )
    assert response.status_code == 404
