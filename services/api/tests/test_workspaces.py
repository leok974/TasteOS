import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db import get_db
from app.models import Workspace

# --- Test Database Setup ---
# Reuse the session scope logic
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_workspaces.db")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Workspace.__table__.create(bind=engine)
    yield
    Workspace.__table__.drop(bind=engine)

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
def db():
    """Direct database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

# --- Tests ---

def test_list_workspaces(client):
    resp = client.get("/api/workspaces/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Database might be empty or seeded.
    # Since we are using a separate test db file per test file if using sqlite, 
    # lets ensuring we create one if empty?
    # Actually, we should probably auto-seed one if list is empty to match logic,
    # OR create one in the test. 
    # The 'get_workspace' dep auto-fails if none exist, but 'list_workspaces' just returns list.

def test_create_workspace(client):
    name = "Test Workspace"
    resp = client.post("/api/workspaces/", json={"name": name})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == name
    assert data["slug"] == "test-workspace"
    assert "id" in data

def test_create_workspace_duplicate_slug(client):
    # First create
    client.post("/api/workspaces/", json={"name": "Collision Test"})
    
    # Second create with same name
    resp = client.post("/api/workspaces/", json={"name": "Collision Test"})
    assert resp.status_code == 200
    data = resp.json()
    # verify slug uniqueness
    assert data["slug"] != "collision-test" 
    assert data["slug"].startswith("collision-test-")

def test_workspace_resolution_header_uuid(client, db):
    # Ensure at least one workspace exists
    ws = db.query(Workspace).first()
    if not ws:
        # Create one manually
        resp = client.post("/api/workspaces/", json={"name": "Setup WS"})
        ws_id = resp.json()["id"]
        ws = db.get(Workspace, ws_id)
        
    # Request with UUID header. 
    # Use generic endpoint like /api/recipes/ which requires workspace
    headers = {"X-Workspace-Id": str(ws.id)}
    resp = client.get("/api/recipes/", headers=headers)
    # 200 OK means dependency passed
    assert resp.status_code == 200

def test_workspace_resolution_header_slug(client, db):
    ws = db.query(Workspace).first()
    if not ws:
        resp = client.post("/api/workspaces/", json={"name": "Setup WS 2"})
        ws_id = resp.json()["id"]
        # refresh from db to get slug accurately if needed, though POST returns it
        ws = db.get(Workspace, ws_id)
    
    headers = {"X-Workspace-Id": ws.slug}
    resp = client.get("/api/recipes/", headers=headers)
    assert resp.status_code == 200

def test_workspace_resolution_invalid_header(client):
    headers = {"X-Workspace-Id": "invalid-slug-12345"}
    resp = client.get("/api/recipes/", headers=headers)
    assert resp.status_code == 404
