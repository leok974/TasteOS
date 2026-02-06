"""Tests for Cook Assist v13.1 AutoFlow logic."""

import pytest
from app.models import Recipe, RecipeStep, CookSession

def test_next_action_checklist_fresh(client, workspace, db_session):
    """Test fresh checklist suggests review (or nothing), NOT 'mark complete'."""
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
        status="active",
        current_step_index=0
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
    # Should NOT have "mark_step_done" action
    action_types = [a["type"] for a in data["actions"]]
    assert "mark_step_done" not in action_types

def test_next_action_checklist_partial(client, workspace, db_session):
    """Test partial checklist suggests 'mark complete'."""
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
        status="active",
        current_step_index=0,
        step_checks={"0": {"0": True}} # Partial check
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
    # Expect Mark Step Done
    action_types = [a["type"] for a in data["actions"]]
    assert "mark_step_done" in action_types
    assert data["suggested_step_idx"] == 0


def test_next_action_checklist_complete(client, workspace, db_session):
    """Test complete checklist suggests YES next step."""
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
        status="active",
        current_step_index=0,
        step_checks={"0": {"0": True, "1": True}} # All checked
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
    action_types = [a["type"] for a in data["actions"]]
    assert "go_to_step" in action_types
    assert data["suggested_step_idx"] == 1



def test_next_action_timer_required_fresh(client, workspace, db_session):
    """Test fresh step WITH timer suggests creating/starting timer (NOT checklist)."""
    recipe = Recipe(workspace_id=workspace.id, title="Timer Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Boil pasta",
        bullets=["Add pasta", "Wait"],
        minutes_est=10
    )
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        current_step_index=0
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(f"/api/cook/session/{session.id}/next", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    action_types = [a["type"] for a in data["actions"]]
    
    # Must suggest CREATE timer first
    assert "create_timer" in action_types
    # Must NOT suggest mark complete
    assert "mark_step_done" not in action_types

def test_next_action_timer_required_running(client, workspace, db_session):
    """Test step with running timer suggests WAIT."""
    recipe = Recipe(workspace_id=workspace.id, title="Timer Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Boil pasta",
        bullets=["Add pasta", "Wait"],
        minutes_est=10
    )
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        current_step_index=0,
        timers={
            "t1": {
                "id": "t1",
                "step_index": 0,
                "duration_sec": 600,
                "state": "running",
                "label": "Pasta"
            }
        }
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(f"/api/cook/session/{session.id}/next", headers=headers)
    
    data = response.json()
    action_types = [a["type"] for a in data["actions"]]
    
    assert "wait_timer" in action_types
    assert "mark_step_done" not in action_types

def test_next_action_checklist_partial_no_timer(client, workspace, db_session):
    """Test partial checklist without timer suggests mark complete."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Chop",
        bullets=["A", "B"]
    )
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        current_step_index=0,
        step_checks={"0": {"0": True}}
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(f"/api/cook/session/{session.id}/next", headers=headers)
    
    data = response.json()
    action_types = [a["type"] for a in data["actions"]]
    assert "mark_step_done" in action_types

def test_next_action_timer_done_allows_next(client, workspace, db_session):
    """Test timer done logic."""
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    step1 = RecipeStep(
        recipe_id=recipe.id, 
        step_index=0, 
        title="Chop",
        bullets=["A"],
        minutes_est=5
    )
    step2 = RecipeStep(recipe_id=recipe.id, step_index=1, title="Done")
    db_session.add_all([step1, step2])
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        status="active",
        current_step_index=0,
        timers={
            "t1": {
                "step_index": 0,
                "state": "done"
            }
        },
        step_checks={"0": {"0": True}} # Checks done too
    )
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.get(f"/api/cook/session/{session.id}/next", headers=headers)
    
    data = response.json()
    action_types = [a["type"] for a in data["actions"]]
    assert "go_to_step" in action_types

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
