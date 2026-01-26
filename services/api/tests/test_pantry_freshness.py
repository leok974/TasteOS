
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import PantryItem, Workspace
from app.main import app

def test_pantry_use_soon_endpoint(client: TestClient, db_session: Session):
    # Setup: Create workspace
    response = client.post("/api/workspaces/", json={"name": "Freshness Test"})
    assert response.status_code == 200

    ws_id = response.json()["id"]
    
    # Headers
    headers = {"X-Workspace-ID": ws_id}
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    # Create Items
    # 1. Expiring Today (Should match)
    client.post("/api/pantry/", json={
        "name": "Milk",
        "expires_on": today.isoformat(),
        "category": "Dairy"
    }, headers=headers)
    
    # 2. Expiring Tomorrow (Should match default 5 days)
    client.post("/api/pantry/", json={
        "name": "Chicken",
        "expires_on": tomorrow.isoformat(),
        "category": "Meat"
    }, headers=headers)
    
    # 3. Expiring Next Week (Should NOT match default 5 days)
    client.post("/api/pantry/", json={
        "name": "Canned Beans",
        "expires_on": next_week.isoformat(),
        "category": "Pantry"
    }, headers=headers)
    
    # 4. No Expiry (Should NOT match)
    client.post("/api/pantry/", json={
        "name": "Salt"
    }, headers=headers)

    # Test Default (days=5)
    resp = client.get("/api/pantry/use-soon", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    
    # Expect Milk and Chicken
    item_names = [i["name"] for i in items]
    assert "Milk" in item_names
    assert "Chicken" in item_names
    assert "Canned Beans" not in item_names
    assert "Salt" not in item_names
    
    # Check Sorting (Milk today < Chicken tomorrow)
    assert items[0]["name"] == "Milk"
    
    # Test Query Param (days=10) -> Should include Canned Beans
    resp = client.get("/api/pantry/use-soon?days=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    item_names = [i["name"] for i in items]
    
    assert "Canned Beans" in item_names
    assert "Milk" in item_names
    
    # Test Opened On field existence
    resp = client.post("/api/pantry/", json={
        "name": "Open Sauce",
        "opened_on": today.isoformat()
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["opened_on"] == today.isoformat()
