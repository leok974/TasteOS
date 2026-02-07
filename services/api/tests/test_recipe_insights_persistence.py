
import pytest
from unittest.mock import MagicMock, patch
from app.models import Recipe, RecipeMacroEntry, RecipeTipEntry

# Helper to create a recipe
def create_recipe(client):
    res = client.post("/api/workspaces/current/recipes", json={
        "title": "Test Recipe for Insights",
        "servings": 4,
        "time_minutes": 30
    })
    # If the endpoint assumes a workspace context or differs, we might need adjustments.
    # Checking test_recipes.py, it seems we might need to rely on seed or specific creation.
    # However, let's try the standard creation endpoint if it exists.
    # If that fails, we can manually insert via DB session if we had access, but client is better.
    # Let's fallback to 'seed' if this is hard, but usually POST /recipes is standard.
    # Actually, looking at previous file list, I didn't see a clear "create recipe" test on the router.
    # I'll rely on the fact that I can just insert one if the client fixture enables DB access, 
    # but the client fixture in conftest usually doesn't expose the session directly easily to the test function without a fixture.
    # Let's try to 'seed' first to ensure a recipe exists.
    return res

def get_first_recipe_id(client):
    # Seed to ensure we have data
    client.post("/api/dev/seed")
    # List recipes
    res = client.get("/api/recipes")
    if res.status_code == 200 and len(res.json()) > 0:
        return res.json()[0]["id"]
    return None

def test_save_and_fetch_macros_manual(client):
    """Test manually saving macros and fetching them back."""
    recipe_id = get_first_recipe_id(client)
    assert recipe_id is not None, "Could not get a recipe ID"

    # 1. Verify initially empty or whatever default
    import app.routers.recipes
    print(f"DEBUG: recipes file is {app.routers.recipes.__file__}")
    res = client.get(f"/api/recipes/{recipe_id}/macros")
    if res.status_code == 404:
        print(client.get("/debug_routes").json())
    # It might return null if nothing saved, or 404? Implementation returns None (null in JSON)
    assert res.status_code == 200
    
    # 2. Save macros
    payload = {
        "source": "user",
        "calories_min": 500,
        "calories_max": 600,
        "protein_min": 20,
        "protein_max": 30
    }
    res = client.post(f"/api/recipes/{recipe_id}/macros", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "user"
    assert data["calories_min"] == 500
    
    # 3. Fetch again
    res = client.get(f"/api/recipes/{recipe_id}/macros")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["source"] == "user"
    assert fetched["calories_max"] == 600

def test_save_and_fetch_tips_manual(client):
    """Test manually saving tips and fetching them back."""
    recipe_id = get_first_recipe_id(client)
    assert recipe_id is not None
    
    scope = "storage"
    
    # 1. Save tips
    payload = {
        "source": "user",
        "tips_json": ["Store in airtight container", "Keep refrigerated"],
        "food_safety_json": [],
        "scope": scope
    }
    # Note: scope is a query param for GET, but payload field for POST?
    # Let's check the router implementation:
    # POST path: /recipes/{id}/tips?scope=...
    # The payload (RecipeTipEntryCreate) might not need scope if it's in the query?
    # Wait, the router sig: def save_recipe_tips(..., scope: str = Query(...), payload: RecipeTipEntryCreate)
    # The payload model `RecipeTipEntryCreate` probably doesn't have scope if it's in the URL, or it ignores it.
    # But let's pass it in query.
    
    res = client.post(f"/api/recipes/{recipe_id}/tips?scope={scope}", json=payload)
    assert res.status_code == 200
    
    # 2. Fetch
    res = client.get(f"/api/recipes/{recipe_id}/tips?scope={scope}")
    assert res.status_code == 200
    data = res.json()
    assert len(data["tips_json"]) == 2
    assert data["tips_json"][0] == "Store in airtight container"
    assert data["source"] == "user"

@patch("app.services.ai_service.AIService.summarize_macros")
def test_estimate_macros_persistence(mock_summarize, client):
    """Test that estimating with persist=true saves the data with source=ai."""
    recipe_id = get_first_recipe_id(client)
    assert recipe_id is not None
    
    # Setup mock return
    mock_result = MagicMock()
    mock_result.source = "ai"
    mock_result.confidence = "high"
    mock_result.calories_range = {"min": 800, "max": 900}
    mock_result.protein_range = {"min": 40, "max": 50}
    mock_summarize.return_value = mock_result
    
    # Call estimate with persist=true
    # Endpoint: POST /recipes/{id}/macros/estimate
    # Body: EstimateMacrosRequest(persist=True)
    res = client.post(f"/api/recipes/{recipe_id}/macros/estimate", json={"persist": True})
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "ai"
    assert data["calories_min"] == 800
    
    # Verify it persists by fetching
    res = client.get(f"/api/recipes/{recipe_id}/macros")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["source"] == "ai"
    assert fetched["confidence"] == 0.9  # Logic maps "high" -> 0.9

@patch("app.services.ai_service.AIService.generate_tips")
def test_estimate_tips_heuristic(mock_generate, client):
    """Test that if AI service returns heuristic source, it is saved as such."""
    recipe_id = get_first_recipe_id(client)
    
    # Setup mock to simulate AI failure falling back to heuristic (or just returning heuristic)
    mock_result = MagicMock()
    mock_result.source = "heuristic"
    mock_result.confidence = "medium"
    mock_result.tips = ["Generic tip 1"]
    mock_result.food_safety = []
    
    # Note: method name in router is generate_tips
    mock_generate.return_value = mock_result
    
    scope = "reheat"
    res = client.post(f"/api/recipes/{recipe_id}/tips/estimate", json={"persist": True, "scope": scope})
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "heuristic"
    assert data["model"] == "heuristic"
    
    # Verify persistence
    res = client.get(f"/api/recipes/{recipe_id}/tips?scope={scope}")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["tips_json"] == ["Generic tip 1"]
