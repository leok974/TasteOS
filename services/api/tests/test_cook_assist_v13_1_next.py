"""Tests for Cook Assist v13.1 AutoFlow logic."""

import pytest
from app.models import Recipe, RecipeStep, CookSession

def test_next_action_checklist_incomplete(client, workspace, db_session):
    """Test next action suggests completing checklist first."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Chop onions",
        bullets=["Peel onion", "Dice finely"]
    )
    step2 = RecipeStep(recipe_id=recipe.id, step_index=1, title="Cook onions")
    db_session.add_all([step1, step2])
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/{session.id}/next",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["suggested_step_idx"] == 0
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "mark_step_done"
    assert action["step_idx"] == 0

def test_next_action_start_timer(client, workspace, db_session):
    """Test next action suggests starting pending timer."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Boil water",
        bullets=[] # No bullets, so checklist valid
    )
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        timers={
            "timer1": {
                "id": "timer1",
                "label": "Boil",
                "step_index": 0,
                "duration_sec": 600,
                "state": "created",
                "created_at": "2026-02-05T12:00:00Z"
            }
        }
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/{session.id}/next",
        headers=headers
    )
    
    data = response.json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "start_timer"
    assert action["timer_id"] == "timer1"

def test_next_action_create_timer(client, workspace, db_session):
    """Test next action suggests creating timer if minute_est present."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Simmer",
        bullets=[],
        minutes_est=10
    )
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/{session.id}/next",
        headers=headers
    )
    
    data = response.json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "create_timer"
    assert action["duration_s"] == 600
    assert action["step_idx"] == 0

def test_next_action_next_step(client, workspace, db_session):
    """Test next action suggests next step when clean."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(recipe_id=recipe.id, step_index=0, title="Step 1")
    step2 = RecipeStep(recipe_id=recipe.id, step_index=1, title="Step 2")
    db_session.add_all([step1, step2])
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/{session.id}/next",
        headers=headers
    )
    
    data = response.json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "go_to_step"
    assert action["step_idx"] == 1
    assert data["suggested_step_idx"] == 1

def test_next_action_complete(client, workspace, db_session):
    """Test next action suggests completion on last step."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(recipe_id=recipe.id, step_index=0, title="Step 1")
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active"
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(
        f"/api/cook/session/{session.id}/next",
        headers=headers
    )
    
    data = response.json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "complete_session"
