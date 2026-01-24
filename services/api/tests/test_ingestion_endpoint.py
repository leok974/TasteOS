from fastapi.testclient import TestClient
from app.main import app
from app.parsing import RuleBasedParser

client = TestClient(app)

def test_ingest_endpoint(db_session, workspace):
    # Mock workspace context is handled by dependency override in conftest usually
    # Assuming workspace fixture provides a workspace and overrides get_workspace
    
    # We need to make sure the parser works in the service context
    # Ideally we mock the parser or just test the full integration if parser is deterministic
    
    text = """
    Test Recipe
    
    Ingredients:
    1 apple
    
    Steps:
    1. Eat it.
    """
    
    # Provide workspace header
    # deps.py: if not UUID, treats as slug. workspace.id="test-ws-id" is not UUID, so it looks for slug "test-ws-id", but slug is "test".
    headers = {"X-Workspace-ID": workspace.slug}
    
    response = client.post(
        "/api/recipes/ingest",
        json={"text": text, "hints": {"servings": 1}},
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"DEBUG: {response.status_code} - {response.text}")

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Test Recipe"
    assert data["servings"] == 1
    assert len(data["steps"]) == 1
