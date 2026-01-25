import pytest
from app.models import Recipe, RecipeStep, CookSession
from datetime import datetime, timezone

def test_adjust_apply_captures_snapshot(client, workspace, db_session):
    # Setup recipe
    recipe = Recipe(workspace_id=workspace.id, title="Soup")
    db_session.add(recipe)
    db_session.commit()
    
    step1 = RecipeStep(recipe_id=recipe.id, step_index=0, title="Boil water", bullets=["Full heat"], minutes_est=10)
    db_session.add(step1)
    db_session.commit()
    
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # Apply adjustment
    new_step = {
        "step_index": 0,
        "title": "Boil water (Adjusted)",
        "bullets": ["Medium heat"],
        "minutes_est": 12
    }
    
    adj_payload = {
        "adjustment_id": "adj-1",
        "step_index": 0,
        "steps_override": [new_step],
        "adjustment": {
            "id": "adj-1",
            "step_index": 0,
            "kind": "fix",
            "title": "Fix heat",
            "bullets": ["Medium heat"],
            "confidence": 0.9,
            "source": "ai"
        }
    }
    
    resp = client.post(
        f"/api/cook/session/{session.id}/adjust/apply",
        json=adj_payload,
        headers=headers
    )
    assert resp.status_code == 200
    
    # Verify snapshot in DB
    db_session.refresh(session)
    log = session.adjustments_log
    assert len(log) == 1
    entry = log[0]
    assert entry["id"] == "adj-1"
    assert "before_step" in entry
    assert entry["before_step"]["bullets"] == ["Full heat"]

def test_undo_restores_step(client, workspace, db_session):
    # Setup recipe & session
    recipe = Recipe(workspace_id=workspace.id, title="SoupUndo")
    db_session.add(recipe)
    db_session.commit()
    step1 = RecipeStep(recipe_id=recipe.id, step_index=0, title="Original", bullets=["Original"], minutes_est=5)
    db_session.add(step1)
    db_session.commit()
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    
    headers = {"X-Workspace-ID": workspace.slug}
    
    # 1. Apply
    client.post(f"/api/cook/session/{session.id}/adjust/apply", json={
        "adjustment_id": "adj-1",
        "step_index": 0,
        "steps_override": [{"step_index":0, "title":"Modified", "bullets":["Modified"], "minutes_est":5}],
        "adjustment": {
            "id": "adj-1", "step_index": 0, "kind": "test", "title": "Mod", "bullets":["Modified"], "confidence":1.0, "source":"test"
        }
    }, headers=headers)
    
    # 2. Undo
    resp = client.post(f"/api/cook/session/{session.id}/adjust/undo", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify overrides reverted
    overrides = data["steps_override"]
    assert overrides[0]["title"] == "Original"
    assert overrides[0]["bullets"] == ["Original"]
    
    # Verify log marked undone
    db_session.refresh(session)
    log = session.adjustments_log
    assert log[0]["undone_at"] is not None

def test_undo_specific_id(client, workspace, db_session):
    # Setup
    recipe = Recipe(workspace_id=workspace.id, title="SoupSpecific")
    db_session.add(recipe)
    db_session.commit()
    step1 = RecipeStep(recipe_id=recipe.id, step_index=0, title="Original", bullets=["Original"], minutes_est=5)
    db_session.add(step1)
    db_session.commit()
    session = CookSession(workspace_id=workspace.id, recipe_id=recipe.id, status="active")
    db_session.add(session)
    db_session.commit()
    headers = {"X-Workspace-ID": workspace.slug}
    
    # Apply 1
    client.post(f"/api/cook/session/{session.id}/adjust/apply", json={
        "adjustment_id": "adj-1", "step_index": 0,
        "steps_override": [{"step_index":0, "title":"Mod1", "bullets":["Mod1"], "minutes_est":5}],
        "adjustment": {"id": "adj-1", "step_index": 0, "kind": "test", "title": "Mod1", "bullets":["Mod1"], "confidence":1.0, "source":"test"}
    }, headers=headers)
    
    # Apply 2 (overwrites)
    client.post(f"/api/cook/session/{session.id}/adjust/apply", json={
        "adjustment_id": "adj-2", "step_index": 0,
        "steps_override": [{"step_index":0, "title":"Mod2", "bullets":["Mod2"], "minutes_est":5}],
        "adjustment": {"id": "adj-2", "step_index": 0, "kind": "test", "title": "Mod2", "bullets":["Mod2"], "confidence":1.0, "source":"test"}
    }, headers=headers)
    
    # Undo adj-2 explicitly
    resp = client.post(f"/api/cook/session/{session.id}/adjust/undo", json={"adjustment_id": "adj-2"}, headers=headers)
    assert resp.status_code == 200
    overrides = resp.json()["steps_override"]
    
    # Should revert to BEFORE act-2, which is Mod1
    assert overrides[0]["title"] == "Mod1"
