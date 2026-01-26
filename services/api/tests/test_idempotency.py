import pytest
import uuid
import json
from unittest.mock import patch, AsyncMock
from fakeredis import FakeAsyncRedis
from app.infra.idempotency import idempotency_precheck, idempotency_store_result
from app.infra import idempotency
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

# --- Mocking Redis ---

@pytest.fixture
def fake_redis():
    return FakeAsyncRedis(decode_responses=True)

@pytest.fixture(autouse=True)
def patch_redis_client(fake_redis):
    # Patch the get_redis used inside idempotency module
    with patch("app.infra.idempotency.get_redis", return_value=fake_redis):
        yield

# --- Unit Tests for Logic ---

@pytest.mark.asyncio
async def test_idempotency_precheck_missing_header():
    req = AsyncMock(spec=Request)
    req.headers = {}
    
    with pytest.raises(HTTPException) as exc:
        await idempotency_precheck(req, workspace_id="ws1", route_key="test")
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_idempotency_flow(fake_redis):
    # Setup
    workspace_id = "ws1"
    route = "test_route"
    idem_key = str(uuid.uuid4())
    
    req = AsyncMock(spec=Request)
    req.headers = {"Idempotency-Key": idem_key}
    req.method = "POST"
    req.url.path = "/test"
    req.body = AsyncMock(return_value=b'{"foo": "bar"}')
    
    # 1. First call -> returns key to proceed
    res = await idempotency_precheck(req, workspace_id=workspace_id, route_key=route)
    assert isinstance(res, tuple)
    rkey, rhash, body = res
    assert rkey.endswith(idem_key)
    assert b"foo" in body
    
    # Check redis state: "processing"
    val = await fake_redis.get(rkey)
    data = json.loads(val)
    assert data["state"] == "processing"
    
    # 2. Second concurrent call -> 409
    with pytest.raises(HTTPException) as exc:
         await idempotency_precheck(req, workspace_id=workspace_id, route_key=route)
    assert exc.value.status_code == 409
    
    # 3. Store result
    await idempotency_store_result(rkey, rhash, status=201, body={"created": True})
    
    # Check redis state: "done"
    val = await fake_redis.get(rkey)
    data = json.loads(val)
    assert data["state"] == "done"
    assert data["status"] == 201
    assert data["body"]["created"] is True
    
    # 4. Third call -> returns cached response
    res2 = await idempotency_precheck(req, workspace_id=workspace_id, route_key=route)
    assert isinstance(res2, JSONResponse)
    assert json.loads(res2.body) == {"created": True}
    assert res2.status_code == 201

# --- Integration Test with DB and Client ---

def test_note_creation_idempotency(client, db_session, workspace):
    """Verify that calling the API twice creates only one note."""
    
    # Force client to use the same DB session to avoid SQLite isolation issues
    from app.db import get_db
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db_session

    # Create fake recipe in DB
    from app.models import Recipe, RecipeNoteEntry
    recipe_id = str(uuid.uuid4())
    r = Recipe(id=recipe_id, workspace_id=workspace.id, title="Test Recipe")
    db_session.add(r)
    db_session.commit()
    
    idem_key = str(uuid.uuid4())
    headers = {
        "X-Workspace-Id": workspace.id,
        "Idempotency-Key": idem_key
    }
    payload = {
        "source": "user",
        "title": "My Note",
        "content_md": "This is a test note",
        "apply_to_recipe_notes": False
    }
    
    # 1. First Call
    resp1 = client.post(f"/recipes/{recipe_id}/notes", json=payload, headers=headers)
    assert resp1.status_code == 200, resp1.text
    note1 = resp1.json()
    
    # 2. Second Call (Same Key)
    resp2 = client.post(f"/recipes/{recipe_id}/notes", json=payload, headers=headers)
    assert resp2.status_code == 200, resp2.text
    note2 = resp2.json()
    
    # IDs should match (cached response)
    assert note1["id"] == note2["id"]
    
    # Verify DB count
    count = db_session.query(RecipeNoteEntry).filter(RecipeNoteEntry.recipe_id == recipe_id).count()
    assert count == 1, "Should have created only 1 note entry"

