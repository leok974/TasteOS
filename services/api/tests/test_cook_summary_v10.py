import pytest
from datetime import datetime, timezone
from app.models import Recipe, CookSession
from app.schemas import SessionNotesApplyRequest

def test_summary_flow(client, workspace, db_session):
    # Setup
    recipe = Recipe(workspace_id=workspace.id, title="Summary Recipe", notes="Existing notes.")
    db_session.add(recipe)
    db_session.commit()
    
    session = CookSession(
        workspace_id=workspace.id, 
        recipe_id=recipe.id, 
        status="active",
        servings_base=2,
        servings_target=4,
        method_key="Air Fryer",
        adjustments_log=[{"fix_summary": "Too salty -> Add sugar"}]
    )
    db_session.add(session)
    db_session.commit()

    headers = {"X-Workspace-ID": workspace.slug}

    # 1. Complete Session
    resp = client.post(f"/api/cook/session/{session.id}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    
    # Verify DB
    db_session.refresh(session)
    assert session.status == "done"
    assert session.completed_at is not None
    assert session.ended_reason == "completed"

    # 2. Get Summary
    resp = client.get(f"/api/cook/session/{session.id}/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["session"]["status"] == "done"
    assert "Cooked with 'Air Fryer' method" in data["highlights"]
    assert "Scaled servings 2 -> 4" in data["highlights"]
    assert "Applied 1 adjustments" in data["highlights"]
    assert data["stats"]["adjustments_total"] == 1
    
    # 3. Preview Notes
    resp = client.post(
        f"/api/cook/session/{session.id}/notes/preview",
        json={
            "include": {
                "method": True, 
                "servings": True, 
                "adjustments": True,
                "freeform": "My custom note"
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    proposal = resp.json()["proposal"]
    notes = proposal["recipe_patch"]["notes_append"]
    
    assert "My custom note" in notes
    assert "Cooked with Air Fryer method." in notes
    assert "Scaled to 4 servings." in notes
    assert any("Too salty" in n for n in notes)

    # 4. Apply Notes
    resp = client.post(
        f"/api/cook/session/{session.id}/notes/apply",
        json={
            "recipe_id": recipe.id,
            "notes_append": notes
        },
        headers=headers
    )
    assert resp.status_code == 200
    
    # Verify Recipe Updated
    db_session.refresh(recipe)
    assert "Existing notes." in recipe.notes
    assert "Cook Session" in recipe.notes
    assert "My custom note" in recipe.notes
