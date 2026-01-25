import pytest
from datetime import datetime, timedelta, timezone
from app.models import Recipe, CookSession

def test_timer_lifecycle_v9(client, workspace, db_session):
    # Setup
    recipe = Recipe(workspace_id=workspace.id, title="Timer Recipe")
    db_session.add(recipe)
    db_session.commit()
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 1. Create Timer
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_create": {
                "step_index": 0,
                "label": "Eggs",
                "duration_sec": 300
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    timers = data["timers"]
    assert len(timers) == 1
    timer_id = list(timers.keys())[0]
    timer = timers[timer_id]
    assert timer["state"] == "created"
    assert timer["duration_sec"] == 300
    assert timer.get("remaining_sec") is None
    assert timer.get("due_at") is None

    # 2. Start Timer
    # Should set due_at = now + 300
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "start"
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    timer = resp.json()["timers"][timer_id]
    assert timer["state"] == "running"
    assert timer["due_at"] is not None
    assert timer["started_at"] is not None
    
    # Check due_at is roughly now + 300s
    due_at = datetime.fromisoformat(timer["due_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    # due_at should be in future
    assert due_at > now
    # roughly 300s diff
    diff = (due_at - now).total_seconds()
    assert 290 < diff < 310

    # 3. Pause Timer (after mild delay simulation? No need to sleep, just check logic)
    # Logic: remaining = due_at - now
    # Since we act immediately, remaining should be ~300
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "pause"
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    timer = resp.json()["timers"][timer_id]
    assert timer["state"] == "paused"
    assert timer["due_at"] is None
    assert timer["started_at"] is None # Spec says clear started_at
    assert timer["remaining_sec"] is not None
    assert 290 < timer["remaining_sec"] <= 300

    # 4. Resume Timer
    # Logic: due_at = now + remaining_sec
    # Let's say we had 299 remaining. New due_at should be now + 299
    
    # Manually hack DB to simulate time passing behavior if we want strict calc check?
    # Or just rely on the fact that remaining_sec was saved.
    
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "start"
            }
        },
        headers=headers
    )
    timer = resp.json()["timers"][timer_id]
    assert timer["state"] == "running"
    assert timer["remaining_sec"] is None # Should be cleared
    assert timer["due_at"] is not None
    
    due_at_resume = datetime.fromisoformat(timer["due_at"].replace("Z", "+00:00"))
    now_resume = datetime.now(timezone.utc)
    diff_resume = (due_at_resume - now_resume).total_seconds()
    assert 290 < diff_resume <= 300

    # 5. Done
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "done"
            }
        },
        headers=headers
    )
    timer = resp.json()["timers"][timer_id]
    assert timer["state"] == "done"
    assert timer.get("due_at") is None
    assert timer.get("remaining_sec") is None

    # 6. Delete
    resp = client.patch(
        f"/api/cook/session/{session.id}",
        json={
            "timer_action": {
                "timer_id": timer_id,
                "action": "delete"
            }
        },
        headers=headers
    )
    timers = resp.json()["timers"]
    assert timer_id not in timers
