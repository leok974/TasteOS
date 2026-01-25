"""Tests for Cook Assist v6 Session Events."""

import pytest
from app.models import Recipe, CookSession

def test_cook_session_events_logging(client, workspace, db_session):
    """Test full flow of events logging."""
    # 1. Setup Recipe
    recipe = Recipe(workspace_id=workspace.id, title="Events Test Recipe", servings=2)
    db_session.add(recipe)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 2. Start Session
    resp = client.post(
        "/api/cook/session/start",
        json={"recipe_id": recipe.id},
        headers=headers
    )
    assert resp.status_code == 200
    session_id = resp.json()["id"]
    
    # 3. Verify Start Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert events[0]["type"] == "session_start"
    assert events[0]["meta"]["recipe_id"] == recipe.id

    # 4. Navigate Step
    resp = client.patch(
        f"/api/cook/session/{session_id}",
        json={"current_step_index": 1},
        headers=headers
    )
    assert resp.status_code == 200
    
    # Verify Navigate Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    events = resp.json()
    assert events[0]["type"] == "step_navigate"
    assert events[0]["meta"]["to"] == 1
    
    # 5. Check Item
    resp = client.patch(
        f"/api/cook/session/{session_id}",
        json={
            "step_checks_patch": {
                "step_index": 1,
                "bullet_index": 0,
                "checked": True
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    
    # Verify Check Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    events = resp.json()
    assert events[0]["type"] == "check_step"
    assert events[0]["meta"]["bullet"] == 0
    
    # 6. Timer Lifecycle
    # Create
    resp = client.patch(
        f"/api/cook/session/{session_id}",
        json={
            "timer_create": {
                "step_index": 1,
                "label": "Test Timer",
                "duration_sec": 60
            }
        },
        headers=headers
    )
    timer_id = list(resp.json()["timers"].keys())[0]
    
    # Verify Create Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    events = resp.json()
    assert events[0]["type"] == "timer_create"
    
    # Start
    resp = client.patch(
        f"/api/cook/session/{session_id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "start"
            }
        },
        headers=headers
    )
    
    # Verify Start Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    events = resp.json()
    assert events[0]["type"] == "timer_start"

    # 7. End Session
    resp = client.patch(
        f"/api/cook/session/{session_id}/end",
        params={"action": "complete"},
        headers=headers
    )
    assert resp.status_code == 200

    # Verify Complete Event
    resp = client.get(f"/api/cook/session/{session_id}/events/recent", headers=headers)
    events = resp.json()
    assert events[0]["type"] == "session_complete"
