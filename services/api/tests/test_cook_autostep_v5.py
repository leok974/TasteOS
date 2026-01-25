"""Tests for Cook Assist v5 (Step Auto-Detection)."""

import pytest
from datetime import datetime, timedelta, timezone
from app.models import Recipe, RecipeStep, CookSession

def test_auto_step_suggest(client, workspace, db_session):
    # Setup Recip & Session
    recipe = Recipe(workspace_id=workspace.id, title="Auto Step Recipe")
    db_session.add(recipe)
    db_session.flush()
    
    steps = []
    for i in range(5):
        steps.append(RecipeStep(
            recipe_id=recipe.id,
            step_index=i,
            title=f"Step {i}",
            bullets=["Do something", "Do another thing"]
        ))
    db_session.add_all(steps)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 1. Enable Auto-Step
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={"auto_step_enabled": True},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["auto_step_enabled"] is True
    
    # 2. Check bullets logic (Step mostly complete)
    # Check 1/2 bullets on step 0 -> 50%
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "step_checks_patch": {
                "step_index": 0,
                "bullet_index": 0,
                "checked": True
            }
        }, headers=headers
    )
    data = response.json()
    # 50% < 80% -> should fallback to current step (0) with low confidence
    assert data["auto_step_suggested_index"] == 0 
    assert data["auto_step_confidence"] <= 0.4
    
    # Check 2/2 -> 100%
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "step_checks_patch": {
                "step_index": 0,
                "bullet_index": 1,
                "checked": True
            }
        }, headers=headers
    )
    # 100% checked -> suggest 1
    data = response.json()
    assert data["auto_step_suggested_index"] == 1
    assert data["auto_step_confidence"] >= 0.7
    assert data["auto_step_reason"] == "Step mostly complete"
    
    # 3. Manual Override interaction
    # Move to step 2 manually
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={"current_step_index": 2},
        headers=headers
    )
    data = response.json()
    # Interaction suggests 2 (conf 0.75), but override cap -> <= 0.4
    assert data["current_step_index"] == 2
    assert data["auto_step_suggested_index"] == 2
    assert data["auto_step_confidence"] <= 0.4
    
    # 4. Timer Running
    # Create timer on step 4
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_create": {
                "step_index": 4,
                "bullet_index": 0,
                "label": "Test Timer",
                "duration_sec": 60
            }
        }, headers=headers
    )
    data = response.json()
    
    timers = data["timers"]
    timer_id = list(timers.keys())[0]
    
    # Start timer
    # Note: Logic in auto_step.py checks "running" state
    # But override from step 3 is still active (3 mins duration).
    # We need to expire it to test high confidence.
    session_obj = db_session.get(CookSession, session.id)
    session_obj.manual_override_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "start"
            }
        }, headers=headers
    )
    data = response.json()
    # Timer running on step 4 -> suggest 4 (conf 0.8)
    assert data["auto_step_suggested_index"] == 4
    assert data["auto_step_confidence"] >= 0.8
    assert data["auto_step_reason"] == "Timer running"
    
def test_auto_jump_mode(client, workspace, db_session):
    recipe = Recipe(workspace_id=workspace.id, title="Auto Jump")
    db_session.add(recipe)
    db_session.flush()
    
    step = RecipeStep(recipe_id=recipe.id, step_index=0, title="S0", bullets=["A"])
    db_session.add(step)
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # Enable auto_jump
    client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "auto_step_enabled": True,
            "auto_step_mode": "auto_jump"
        }, headers=headers
    )
    
    # Create timer on step 5
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_create": {
                "step_index": 5, 
                "bullet_index": 0,
                "label": "Jump Timer",
                "duration_sec": 60
            }
        }, headers=headers
    )
    data = response.json()
    timers = data["timers"]
    timer_id = list(timers.keys())[0]
    
    # Start timer -> high confidence signal -> auto jump
    response = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "start"
            }
        }, headers=headers
    )
    data = response.json()
    assert data["current_step_index"] == 5
