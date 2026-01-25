
"""Tests for Cook Assist v3 (Method Switcher)."""

import pytest
from app.models import Recipe, RecipeStep, CookSession

def test_get_methods(client, workspace):
    """Test retrieving available cooking methods."""
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get("/api/cook/methods", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert len(data["methods"]) > 0
    
    method_keys = [m["key"] for m in data["methods"]]
    assert "air_fryer" in method_keys
    assert "instant_pot" in method_keys

def test_method_preview_air_fryer(client, workspace, db_session):
    """Test generating a preview for Air Fryer method."""
    recipe = Recipe(workspace_id=workspace.id, title="Chicken Wings", time_minutes=60)
    db_session.add(recipe)
    db_session.commit()
    
    # Add a cook step
    step1 = RecipeStep(
        recipe_id=recipe.id,
        step_index=0,
        title="Bake Chicken",
        bullets=["Bake at 400F for 45 mins"],
        minutes_est=45
    )
    db_session.add(step1)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        f"/api/cook/session/{session.id}/method/preview",
        json={"method_key": "air_fryer"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check tradeoffs
    assert data["tradeoffs"]["cleanup"] == "low"
    # Time delta should be approx -20% of 60 mins = -12 mins, or based on generator logic
    assert data["tradeoffs"]["time_delta_min"] < 0
    
    # Check steps
    steps = data["steps_preview"]
    assert len(steps) > 0
    assert "Air Fry" in steps[0]["title"]

def test_method_apply_and_reset(client, workspace, db_session):
    """Test applying and then resetting a method override."""
    recipe = Recipe(workspace_id=workspace.id, title="Stew")
    db_session.add(recipe)
    db_session.commit()
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 1. Apply Override
    fake_steps = [{"step_index": 0, "title": "Air Fry Step", "bullets": ["Do it"], "minutes_est": 10}]
    fake_tradeoffs = {"time_delta_min": -10}
    
    response = client.post(
        f"/api/cook/session/{session.id}/method/apply",
        json={
            "method_key": "air_fryer",
            "steps_override": fake_steps,
            "method_tradeoffs": fake_tradeoffs
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["method_key"] == "air_fryer"
    assert data["steps_override"] == fake_steps
    
    # Verify persistence
    db_session.expire_all()
    curr_session = db_session.get(CookSession, session.id)
    assert curr_session.method_key == "air_fryer"
    
    # 2. Reset
    response = client.post(
        f"/api/cook/session/{session.id}/method/reset",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["method_key"] is None
    assert data["steps_override"] is None
    
    db_session.refresh(curr_session)
    assert curr_session.method_key is None
