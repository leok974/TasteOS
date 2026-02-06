import pytest
import uuid
from app.models import Recipe, RecipeStep
from app.parsing.timers import generate_suggestions_for_step
from app.schemas import TimerSuggestion

# Fixtures

@pytest.fixture
def test_user_id():
    return str(uuid.uuid4())

@pytest.fixture
def test_recipe(db_session, workspace):
    r = Recipe(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        title="Test Recipe",
        steps=[
            RecipeStep(step_index=0, title="Prep", minutes_est=10, bullets=[])
        ]
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r

# Tests

def test_generate_suggestions_minutes_est():
    step = RecipeStep(step_index=0, title="Boil", minutes_est=10, bullets=[])
    suggestions = generate_suggestions_for_step(step, 0)
    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.duration_s == 600
    assert s.label == "Boil"
    assert s.reason == "minutes_est"
    assert s.client_id == "step-0-est-600"

def test_generate_suggestions_regex():
    step = RecipeStep(step_index=1, title="Bake", minutes_est=0, bullets=[
        "Bake for 30 minutes until golden.",
        "Let cool for 10 mins."
    ])
    suggestions = generate_suggestions_for_step(step, 1)
    
    # Expect 2 suggestions: 30 mins (Bake) and 10 mins (Cool)
    assert len(suggestions) == 2
    
    s1 = next((s for s in suggestions if s.duration_s == 1800), None)
    assert s1 is not None
    assert s1.label == "Bake" # From title or keyword
    assert "text_regex" in s1.reason
    
    s2 = next((s for s in suggestions if s.duration_s == 600), None)
    assert s2 is not None
    assert s2.label == "Cool" # From keyword in bullet
    assert "text_regex" in s2.reason

def test_endpoint_suggestions(client, db_session, test_recipe, test_user_id, workspace):
    # Setup session
    response = client.post(
        "/api/cook/session/start",
        json={"recipe_id": test_recipe.id},
        headers={
            "X-User-Id": test_user_id, 
            "X-Workspace-Id": workspace.id,
            "Idempotency-Key": str(uuid.uuid4())
        }
    )
    if response.status_code != 200:
        print(f"Error starting session: {response.text}")
        
    assert response.status_code == 200
    session_id = response.json()["id"]
    
    # Add a step with time text to recipe
    # We update the recipe in DB
    test_recipe.steps = [
         RecipeStep(step_index=0, title="Simmer", minutes_est=5, bullets=["Simmer for 20 minutes"])
    ]
    db_session.commit()
    
    res = client.get(f"/api/cook/session/{session_id}/timers/suggested")
    assert res.status_code == 200
    data = res.json()
    assert "suggested" in data
    # Expect 5 min (est) + 20 min (regex)
    assert len(data["suggested"]) >= 2
    
    s_est = next((s for s in data["suggested"] if s["reason"] == "minutes_est"), None)
    assert s_est["duration_s"] == 300
    
    s_regex = next((s for s in data["suggested"] if s["duration_s"] == 1200), None)
    assert s_regex is not None

def test_create_timers_from_suggested(client, db_session, test_recipe, test_user_id, workspace):
    # Setup recipe with specific step
    test_recipe.steps = [
        RecipeStep(step_index=0, title="Roast", minutes_est=45, bullets=[]) 
    ]
    db_session.commit()

    # Setup session
    response = client.post(
        "/api/cook/session/start", 
        json={"recipe_id": test_recipe.id}, 
        headers={
            "X-User-Id": test_user_id, 
            "X-Workspace-Id": workspace.id,
            "Idempotency-Key": str(uuid.uuid4())
        }
    )
    session_id = response.json()["id"]
    
    # ID: step-0-est-2700
    client_id = f"step-0-est-{45*60}"
    
    # Call create
    res = client.post(f"/api/cook/session/{session_id}/timers/from-suggested", json={
        "client_ids": [client_id],
        "autostart": True
    })
    assert res.status_code == 200
    assert res.json()["created"] == 1
    
    # Verify timer created
    res = client.get(f"/api/cook/session/active?recipe_id={test_recipe.id}")
    timers = res.json()["timers"]
    assert len(timers) == 1
    timer = list(timers.values())[0]
    assert timer["label"] == "Roast"
    assert timer["duration_sec"] == 2700
    assert timer["state"] == "running"
    
    # Call again (Idempotency) - should not create new one
    res = client.post(f"/api/cook/session/{session_id}/timers/from-suggested", json={
        "client_ids": [client_id],
        "autostart": True
    })
    assert res.json()["created"] == 0
    
    # Verify still 1 timer
    res = client.get(f"/api/cook/session/active?recipe_id={test_recipe.id}")
    timers = res.json()["timers"]
    assert len(timers) == 1
