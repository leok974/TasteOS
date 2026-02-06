
import pytest
from datetime import datetime, timezone
import json
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import CookSession, Recipe, Workspace, RecipeStep

@pytest.fixture
def recipe(db_session: Session, workspace: Workspace):
    """Create a test recipe."""
    r = Recipe(
        id="recipe-timer-test",
        workspace_id=workspace.id,
        title="Timer Test Recipe",
        steps=[
            RecipeStep(step_index=0, title="Step 1", bullets=["Boil water"], minutes_est=5),
            RecipeStep(step_index=1, title="Step 2", bullets=["Cook pasta"], minutes_est=10)
        ]
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r

def test_v13_timer_lifecycle(client: TestClient, db_session: Session, workspace: Workspace, recipe: Recipe):
    # 1. Start Session
    resp = client.post(
        f"/api/cook/session/start", 
        json={"recipe_id": recipe.id},
        headers={"Idempotency-Key": "test-v13-start"}
    )
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    # 2. Create Timer
    client_id = "timer-client-1"
    create_payload = {
        "client_id": client_id,
        "label": "Pasta",
        "step_index": 1,
        "duration_s": 600
    }
    resp = client.post(f"/api/cook/session/{session_id}/timers", json=create_payload)
    assert resp.status_code == 200
    t1 = resp.json()
    assert t1["label"] == "Pasta"
    assert t1["state"] == "created"
    
    # 3. Idempotency Check
    resp = client.post(f"/api/cook/session/{session_id}/timers", json=create_payload)
    assert resp.status_code == 200
    t1_dup = resp.json()
    assert t1_dup["id"] == t1["id"] # Same ID returned

    timer_id = t1["id"]

    # 4. Start Timer
    resp = client.post(f"/api/cook/session/{session_id}/timers/{timer_id}/action", json={"action": "start"})
    assert resp.status_code == 200
    t_start = resp.json()
    assert t_start["state"] == "running"
    assert t_start["started_at"] is not None

    # 5. Pause Timer
    resp = client.post(f"/api/cook/session/{session_id}/timers/{timer_id}/action", json={"action": "pause"})
    t_pause = resp.json()
    assert t_pause["state"] == "paused"
    assert t_pause["paused_at"] is not None

    # 6. Resume Timer
    # Ensure resumed start_at is shifted
    original_start = datetime.fromisoformat(t_start["started_at"])
    # Mock time passing if possible? Hard with integration test.
    # Just check state transition.
    resp = client.post(f"/api/cook/session/{session_id}/timers/{timer_id}/action", json={"action": "resume"})
    t_resume = resp.json()
    assert t_resume["state"] == "running"
    assert t_resume["paused_at"] is None
    
    # 7. Patch Timer
    resp = client.patch(f"/api/cook/session/{session_id}/timers/{timer_id}", json={"label": "Pasta Al Dente"})
    assert resp.json()["label"] == "Pasta Al Dente"

    # 8. Done
    resp = client.post(f"/api/cook/session/{session_id}/timers/{timer_id}/action", json={"action": "done"})
    assert resp.json()["state"] == "done"

    # 9. Delete (Soft)
    resp = client.post(f"/api/cook/session/{session_id}/timers/{timer_id}/action", json={"action": "delete"})
    assert resp.json()["deleted_at"] is not None
