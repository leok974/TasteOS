import os
import uuid
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import Recipe, Workspace, RecipeIngredient, RecipeStep
from app.share_schemas import PortableRecipe

# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_share.db")
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
    Base.metadata.create_all(bind=engine) # Ensure tables exist
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Avoid drop_all on sqlite due to constraints issue
        # We can just recreate tables or use a new file for next run

def test_export_import_flow(client, db_session):
    # 1. Setup: Create two workspaces
    
    # Create WS A
    resp_a = client.post("/api/workspaces/", json={"name": "Source Kitchen"})
    assert resp_a.status_code == 200, resp_a.text
    ws_id_a = resp_a.json()["id"]
    headers_ws_a = {"X-Workspace-Id": ws_id_a}

    # Create WS B
    resp_b = client.post("/api/workspaces/", json={"name": "Target Kitchen"})
    assert resp_b.status_code == 200, resp_b.text
    ws_id_b = resp_b.json()["id"]
    headers_ws_b = {"X-Workspace-Id": ws_id_b}

    # 2. Seed Recipe in WS A
    recipe_payload = {
        "title": "Grandma's Cookies",
        "servings": 24,
        "time_minutes": 45,
        "notes": "Secret ingredient is love",
        "cuisines": ["American"],
        "tags": ["Dessert"],
        "ingredients": [
            {"name": "Flour", "qty": 2.5, "unit": "cup", "category": "baking"},
            {"name": "Chocolate Chips", "qty": 1, "unit": "bag", "category": "baking"}
        ],
        "steps": [
            {"step_index": 0, "title": "Mix dry ingredients", "minutes_est": 5},
            {"step_index": 1, "title": "Bake", "minutes_est": 12}
        ]
    }
    
    resp = client.post("/api/recipes", json=recipe_payload, headers=headers_ws_a)
    assert resp.status_code == 201
    recipe_id_a = resp.json()["id"]

    # Manually seed ingredients (since create API doesn't support them yet)
    db_session.add(RecipeIngredient(
        id=str(uuid.uuid4()),
        recipe_id=recipe_id_a,
        name="Flour", qty=2.5, unit="cup", category="baking"
    ))
    db_session.add(RecipeIngredient(
        id=str(uuid.uuid4()),
        recipe_id=recipe_id_a,
        name="Chocolate Chips", qty=1, unit="bag", category="baking"
    ))
    db_session.commit()
    
    # 3. Export form WS A
    export_resp = client.get(f"/api/recipes/{recipe_id_a}/export", headers=headers_ws_a)
    assert export_resp.status_code == 200
    portable_json = export_resp.json()
    
    # Verify portable payload structure
    assert portable_json["schema_version"] == "tasteos.recipe.v1"
    assert portable_json["recipe"]["title"] == "Grandma's Cookies"
    assert len(portable_json["recipe"]["ingredients"]) == 2
    assert len(portable_json["recipe"]["steps"]) == 2
    
    # 4. Import to WS B
    import_resp = client.post("/api/recipes/import", json=portable_json, headers=headers_ws_b)
    assert import_resp.status_code == 201
    import_data = import_resp.json()
    assert import_data["created"] is True
    assert import_data["deduped"] is False
    
    recipe_id_b = import_data["recipe_id"]
    assert recipe_id_b != recipe_id_a # New ID created

    # 5. Verify Isolation & Data in WS B
    # Get recipe in WS B
    get_resp = client.get(f"/api/recipes/{recipe_id_b}", headers=headers_ws_b)
    assert get_resp.status_code == 200
    data_b = get_resp.json()
    assert data_b["title"] == "Grandma's Cookies"
    # Note: List view usually doesn't show steps, but we requested detail?
    # Wait, GET /recipes/{id} DOES return details (RecipeOut)
    assert len(data_b["steps"]) == 2
    
    # Verify ingredients in WS B (Need to check if RecipeOut includes them?)
    # models.Recipe has ingredients relationship. 
    # schemas.RecipeOut DOES NOT include ingredients field! 
    # Let's check schemas.py again.
    # RecipeOut -> lines 87-99. No ingredients.
    # So we can't verify ingredients via API unless we add them to RecipeOut or check DB.
    
    # Using DB to verify ingredients imported correctly
    ingredients_b = db_session.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id_b).all()
    assert len(ingredients_b) == 2
    names_b = {i.name for i in ingredients_b}
    assert "Flour" in names_b
    
    # Verify it acts as a new independent copy
    rec_b = db_session.query(Recipe).filter(Recipe.id == recipe_id_b).first()
    assert rec_b.workspace_id == ws_id_b

def test_deduplication(client):
    resp = client.post("/api/workspaces/", json={"name": "Dedupe Lab"})
    ws_id = resp.json()["id"]
    headers = {"X-Workspace-Id": ws_id}
    
    # Create payload manually
    portable_json = {
        "schema_version": "tasteos.recipe.v1",
        "exported_at": "2024-01-01T00:00:00Z",
        "recipe": {
            "title": "Unique Stew",
            "ingredients": [{"name": "Beef", "qty": 1, "unit": "lb"}],
            "steps": []
        }
    }
    
    # Import Once
    resp1 = client.post("/api/recipes/import", json=portable_json, headers=headers)
    assert resp1.status_code == 201
    assert resp1.json()["created"] is True
    
    # Import Twice (Dedupe)
    resp2 = client.post("/api/recipes/import?mode=dedupe", json=portable_json, headers=headers)
    assert resp2.status_code == 201
    assert resp2.json()["created"] is False
    assert resp2.json()["deduped"] is True
    assert resp2.json()["recipe_id"] == resp1.json()["recipe_id"]
    
    # Import Force Copy
    resp3 = client.post("/api/recipes/import?mode=copy", json=portable_json, headers=headers)
    assert resp3.status_code == 201
    assert resp3.json()["created"] is True
    assert resp3.json()["recipe_id"] != resp1.json()["recipe_id"]

def test_invalid_schema(client):
    resp = client.post("/api/workspaces/", json={"name": "Schema Lab"})
    ws_id = resp.json()["id"]
    headers = {"X-Workspace-Id": ws_id}
    
    bad_payload = {
        "schema_version": "v999",
        "recipe": {"title": "Bad"}
    }
    resp = client.post("/api/recipes/import", json=bad_payload, headers=headers)
    assert resp.status_code == 400
