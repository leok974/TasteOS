"""Tests for Cook Assist v1 API endpoints."""

import pytest
from app.models import Recipe, RecipeStep, RecipeIngredient, CookSession, PantryItem


def test_start_session_creates_new(client, workspace, db_session):
    """Test starting a new cook session."""
    # Create a recipe
    recipe = Recipe(workspace_id=workspace.id,title="Test Recipe", servings=4)
    db_session.add(recipe)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/cook/session/start",
        json={"recipe_id": recipe.id},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipe_id"] == recipe.id
    assert data["status"] == "active"
    assert data["current_step_index"] == 0
    assert data["step_checks"] == {}
    assert data["timers"] == {}


def test_start_session_returns_existing(client, workspace, db_session):
    """Test starting a session returns existing active session."""
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    
    # Create existing session
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/cook/session/start",
        json={"recipe_id": recipe.id},
        headers=headers
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == session.id


def test_get_active_session(client, workspace, db_session):
    """Test retrieving active session."""
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/active?recipe_id={recipe.id}",
        headers=headers
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == session.id


def test_get_active_session_not_found(client, workspace):
    """Test 404 when no active session exists."""
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        "/api/cook/session/active?recipe_id=nonexistent",
        headers=headers
    )
    
    assert response.status_code == 404


def test_patch_session_step_check(client, workspace, db_session):
    """Test toggling step check."""
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "step_checks_patch": {
                "step_index": 0,
                "bullet_index": 1,
                "checked": True
            }
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "0" in data["step_checks"]
    assert data["step_checks"]["0"]["1"] is True


def test_patch_session_timer_create(client, workspace, db_session):
    """Test creating a timer."""
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_create": {
                "step_index": 0,
                "bullet_index": 2,
                "label": "Boil pasta",
                "duration_sec": 300
            }
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    timers = data["timers"]
    assert len(timers) == 1
    timer = list(timers.values())[0]
    assert timer["label"] == "Boil pasta"
    assert timer["duration_sec"] == 300
    assert timer["state"] == "created"


def test_patch_session_timer_actions(client, workspace, db_session):
    """Test timer start/pause/done/delete."""
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        timers={"timer1": {"state": "created", "label": "Test", "duration_sec": 60}}
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # Start timer
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={"timer_action": {"timer_id": "timer1", "action": "start"}},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["timers"]["timer1"]["state"] == "running"
    
    # Pause timer
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={"timer_action": {"timer_id": "timer1", "action": "pause"}},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["timers"]["timer1"]["state"] == "paused"
    
    # Mark done
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={"timer_action": {"timer_id": "timer1", "action": "done"}},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["timers"]["timer1"]["state"] == "done"


def test_cross_workspace_session_isolation(client, workspace, db_session):
    """Test sessions are isolated by workspace."""
    # Create another workspace
    from app.models import Workspace
    other_ws = Workspace(slug="other", name="Other")
    db_session.add(other_ws)
    db_session.commit()
    
    recipe = Recipe(workspace_id=workspace.id, title="Test", servings=4)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    # Try to access from other workspace
    headers = {"X-Workspace-ID": "other"}
    response = client.get(
        f"/api/cook/session/active?recipe_id={recipe.id}",
        headers=headers
    )
    
    assert response.status_code == 404


def test_assist_substitute_intent(client, workspace, db_session):
    """Test assist with substitute intent."""
    recipe = Recipe(workspace_id=workspace.id, title="Pancakes", servings=4)
    db_session.add(recipe)
    
    # Add pantry items
    pantry = [
        PantryItem(workspace_id=workspace.id, name="Milk", source="manual"),
        PantryItem(workspace_id=workspace.id, name="Vinegar", source="manual")
    ]
    db_session.add_all(pantry)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/cook/assist",
        json={
            "recipe_id": recipe.id,
            "step_index": 0,
            "intent": "substitute",
            "payload": {"ingredient": "Buttermilk", "context": "Pancakes"}
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "bullets" in data
    assert data["source"] in ["ai", "rules"]


def test_assist_macros_intent(client, workspace, db_session):
    """Test assist with macros intent."""
    recipe = Recipe(workspace_id=workspace.id, title="Steak", servings=2)
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    
    ing = RecipeIngredient(recipe_id=recipe.id, name="Steak", qty=1, unit="lb")
    db_session.add(ing)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/cook/assist",
        json={
            "recipe_id": recipe.id,
            "step_index": 0,
            "intent": "macros",
            "payload": {}
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nutritional Estimate"
    assert len(data["bullets"]) > 0


def test_assist_fix_intent_rules(client, workspace, db_session):
    """Test assist with fix intent returns deterministic rules."""
    recipe = Recipe(workspace_id=workspace.id, title="Soup", servings=4)
    db_session.add(recipe)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # Test each fix type
    for problem in ["too_salty", "too_spicy", "too_thick", "too_thin"]:
        response = client.post(
            "/api/cook/assist",
            json={
                "recipe_id": recipe.id,
                "step_index": 0,
                "intent": "fix",
                "payload": {"problem": problem}
            },
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "rules"
        assert len(data["bullets"]) >= 3  # At least 3 bullets + why
        assert any("Why:" in b for b in data["bullets"])
