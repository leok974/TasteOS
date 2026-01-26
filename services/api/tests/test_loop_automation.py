import pytest
import uuid
from datetime import datetime, timedelta
from app.models import GroceryList, GroceryListItem, PantryItem

def test_grocery_purchase_sync_to_pantry(client, db_session, workspace):
    """Test that marking a grocery item as purchased syncs to pantry."""
    
    # 1. Create a grocery list with items
    glist = GroceryList(id=str(uuid.uuid4()), workspace_id=workspace.id)
    db_session.add(glist)
    
    item_id = str(uuid.uuid4())
    item = GroceryListItem(
        id=item_id,
        grocery_list_id=glist.id,
        name="Milk",
        qty=1,
        unit="gallon",
        status="need"
    )
    db_session.add(item)
    db_session.commit()
    
    # 2. Patch item to "purchased"
    headers = {"X-Workspace-Id": workspace.id}
    resp = client.patch(f"/api/grocery/items/{item_id}", json={"status": "purchased"}, headers=headers)
    assert resp.status_code == 200, resp.text
    
    # 3. Verify Pantry Item Created
    pantry_item = db_session.query(PantryItem).filter(PantryItem.name == "Milk").first()
    assert pantry_item is not None
    assert pantry_item.source == "grocery"
    assert pantry_item.qty == 1
    
    # 4. Verify Link
    db_session.refresh(item)
    assert item.pantry_item_id == pantry_item.id
    assert item.purchased_at is not None
    
    # 5. Idempotency: Patch again should not create duplicate
    resp2 = client.patch(f"/api/grocery/items/{item_id}", json={"status": "purchased"}, headers=headers)
    assert resp2.status_code == 200
    
    count = db_session.query(PantryItem).filter(PantryItem.name == "Milk").count()
    assert count == 1

def test_pantry_use_soon(client, db_session, workspace):
    """Test finding items satisfying use-soon criteria."""
    
    # 1. Create items
    today = datetime.now().date()
    # Expiring tomorrow
    p1 = PantryItem(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        name="Spinach",
        expires_at=today + timedelta(days=1),
        source="manual"
    )
    # Expiring in 10 days (safe)
    p2 = PantryItem(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        name="Canned Beans",
        expires_at=today + timedelta(days=10),
        source="manual"
    )
    # Explicit use soon (no expiry date but flagged via date)
    p3 = PantryItem(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        name="Leftover Pizza",
        use_soon_at=today,
        source="leftover"
    )
    
    db_session.add_all([p1, p2, p3])
    db_session.commit()
    
    # 2. Query use-soon (default 5 days)
    headers = {"X-Workspace-Id": workspace.id}
    resp = client.get("/api/pantry/use-soon?days=5", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    
    names = [i["name"] for i in items]
    assert "Spinach" in names
    assert "Leftover Pizza" in names
    assert "Canned Beans" not in names

def test_bulk_sync(client, db_session, workspace):
    """Test bulk sync of purchased items."""
    
    glist = GroceryList(id=str(uuid.uuid4()), workspace_id=workspace.id)
    db_session.add(glist)
    
    # Two purchased items, one already synced (simulated), one not
    i1 = GroceryListItem(
        id=str(uuid.uuid4()), grocery_list_id=glist.id, name="Apple", status="purchased"
    )
    i2 = GroceryListItem(
        id=str(uuid.uuid4()), grocery_list_id=glist.id, name="Banana", status="purchased"
    )
    i3 = GroceryListItem(
        id=str(uuid.uuid4()), grocery_list_id=glist.id, name="Carrot", status="need"
    )
    
    db_session.add_all([i1, i2, i3])
    db_session.commit()
    
    # Call bulk sync
    headers = {"X-Workspace-Id": workspace.id}
    resp = client.post("/api/grocery/current/sync-to-pantry", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["synced"] == 2
    assert data["total_purchased"] == 2
    
    # Verify pantry
    assert db_session.query(PantryItem).filter(PantryItem.name == "Apple").first()
    assert db_session.query(PantryItem).filter(PantryItem.name == "Banana").first()
    assert db_session.query(PantryItem).filter(PantryItem.name == "Carrot").first() is None
