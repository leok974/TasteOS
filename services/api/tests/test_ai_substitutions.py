from app.models import PantryItem

def test_substitute_endpoint_mock(client, workspace, db_session):
    # 1. Add pantry items
    items = [
        PantryItem(workspace_id=workspace.id, name="Milk", source="manual"),
        PantryItem(workspace_id=workspace.id, name="Vinegar", source="manual")
    ]
    db_session.add_all(items)
    db_session.commit()
    
    # 2. Call Substitute endpoint asking for Buttermilk
    # The mock service is hardcoded: Buttermilk + (Milk & Vinegar in pantry) -> Success
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/ai/substitute",
        json={"ingredient": "Buttermilk", "context": "Pancakes"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["substitute"] == "Milk + Vinegar"
    assert "Mix 1 cup milk" in data["instruction"]
    assert data["confidence"] == "high"

def test_substitute_endpoint_fallback(client, workspace):
    # No pantry items
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/ai/substitute",
        json={"ingredient": "Saffron", "context": "Paella"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "pantry" in data["substitute"].lower()  # Generic fallback mentions pantry
    assert data["confidence"] == "low"
    assert data["impact"] == "different"
