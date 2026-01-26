
import os
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import Workspace, PantryItem, MealPlan, MealPlanEntry
from app.deps import get_workspace

# --- Test Database Setup ---
# Use the environment's DATABASE_URL (Postgres)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_pantry.db")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    """Test client with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def db_session():
    """Direct database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def workspace(db_session):
    """Create a unique test workspace and cleanup after."""
    slug = f"test-pantry-{uuid.uuid4().hex[:8]}"
    ws = Workspace(name="Test Pantry Workspace", slug=slug)
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)
    
    yield ws
    
    # Cleanup
    # Note: ondelete="CASCADE" in models handles related items
    db_session.delete(ws)
    db_session.commit()

# --- Tests ---

def test_create_pantry_item(client, workspace):
    """Create pantry item works."""
    # We need to simulate the workspace header or ensure resolution finds our workspace
    # The 'local' workspace resolution fallback finds first workspace.
    
    payload = {
        "name": "Milk",
        "qty": 1.0,
        "unit": "gal",
        "category": "dairy",
        "expires_on": str(date.today() + timedelta(days=7))
    }
    
    # Passing header to be explicit
    response = client.post(
        "/api/pantry/", 
        json=payload, 
        headers={"X-Workspace-Id": workspace.id}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Milk"
    assert data["workspace_id"] == workspace.id
    assert data["source"] == "manual"


def test_list_pantry_items(client, workspace):
    """List returns created items."""
    # Create manually
    client.post("/api/pantry/", json={"name": "Eggs"}, headers={"X-Workspace-Id": workspace.id})
    client.post("/api/pantry/", json={"name": "Bread"}, headers={"X-Workspace-Id": workspace.id})
    
    response = client.get("/api/pantry/", headers={"X-Workspace-Id": workspace.id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [i["name"] for i in data]
    assert "Eggs" in names
    assert "Bread" in names


def test_use_soon_filter(client, workspace):
    """use_soon filter returns only expiring items."""
    today = date.today()
    
    # 1. Expires tomorrow (Soon)
    client.post("/api/pantry/", json={
        "name": "Old Milk", "expires_on": str(today + timedelta(days=1))
    }, headers={"X-Workspace-Id": workspace.id})
    
    # 2. Expires in 4 days (Soon)
    client.post("/api/pantry/", json={
        "name": "Yogurt", "expires_on": str(today + timedelta(days=4))
    }, headers={"X-Workspace-Id": workspace.id})
    
    # 3. Expires in 10 days (Not soon)
    client.post("/api/pantry/", json={
        "name": "Canned Beans", "expires_on": str(today + timedelta(days=10))
    }, headers={"X-Workspace-Id": workspace.id})
    
    # 4. No expiry (Not soon)
    client.post("/api/pantry/", json={
        "name": "Salt"
    }, headers={"X-Workspace-Id": workspace.id})
    
    response = client.get("/api/pantry/?use_soon=1", headers={"X-Workspace-Id": workspace.id})
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    names = [i["name"] for i in data]
    assert "Old Milk" in names
    assert "Yogurt" in names
    assert "Canned Beans" not in names
    assert "Salt" not in names


def test_update_pantry_item(client, workspace):
    """Update item fields."""
    res = client.post(
        "/api/pantry/", 
        json={"name": "Apples", "qty": 5}, 
        headers={"X-Workspace-Id": workspace.id}
    )
    item_id = res.json()["id"]
    
    res = client.patch(
        f"/api/pantry/{item_id}",
        json={"qty": 3, "notes": "Ate two"},
        headers={"X-Workspace-Id": workspace.id}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["qty"] == 3.0
    assert data["notes"] == "Ate two"
    assert data["name"] == "Apples"  # Unchanged


def test_delete_pantry_item(client, workspace):
    """Delete removes item."""
    res = client.post(
        "/api/pantry/", 
        json={"name": "Mistake"}, 
        headers={"X-Workspace-Id": workspace.id}
    )
    item_id = res.json()["id"]
    
    res = client.delete(
        f"/api/pantry/{item_id}",
        headers={"X-Workspace-Id": workspace.id}
    )
    assert res.status_code == 204
    
    # Verify gone
    res = client.get("/api/pantry/", headers={"X-Workspace-Id": workspace.id})
    ids = [i["id"] for i in res.json()]
    assert item_id not in ids


# --- Leftovers Tests ---

def test_create_leftover_lifecycle(client, workspace, db_session):
    # 0. Setup: Create Meal Plan Entry for FK
    mp = MealPlan(
        workspace_id=workspace.id,
        week_start=date.today(),
        settings_json={}
    )
    db_session.add(mp)
    db_session.commit()
    db_session.refresh(mp)
    
    mpe = MealPlanEntry(
        meal_plan_id=mp.id,
        date=date.today(),
        meal_type="dinner"
    )
    db_session.add(mpe)
    db_session.commit()
    db_session.refresh(mpe)

    # 1. Create Leftover
    payload = {
        "name": "Roast Chicken Leftovers",
        "servings_left": 2.5,
        "expires_on": (date.today() + timedelta(days=3)).isoformat(),
        "notes": "Delicious",
        "plan_entry_id": mpe.id
    }
    
    headers = {"X-Workspace-Id": workspace.id}
    
    response = client.post("/api/pantry/leftovers", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["pantry_item_id"] is not None
    leftover_id = data["id"]
    p_id = data["pantry_item_id"]

    # 2. Verify Pantry Item Created
    p_response = client.get("/api/pantry/", headers=headers)
    p_items = p_response.json()
    found_p = next((p for p in p_items if p["id"] == p_id), None)
    assert found_p is not None
    assert found_p["name"] == payload["name"]
    assert found_p["category"] == "Leftovers"
    assert found_p["qty"] == 2.5
    assert found_p["source"] == "leftover"

    # 3. Dedupe check (Idempotencyish)
    # Calling create again with same plan_entry_id should return existing
    response2 = client.post("/api/pantry/leftovers", json=payload, headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["id"] == leftover_id
    
    # 4. Verify Active List
    l_response = client.get("/api/pantry/leftovers", headers=headers)
    l_items = l_response.json()
    assert len(l_items) >= 1
    assert any(l["id"] == leftover_id for l in l_items)
