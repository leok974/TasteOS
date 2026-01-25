import pytest
from app.models import CookSession
from app.schemas import SessionResponse

def test_cook_adjust_preview_apply(client, db_session, workspace):
    # 1. Setup Recipe
    recipe_data = {
        "title": "Salty Soup",
        "steps": [
            {"step_index": 0, "title": "Boil water", "bullets": ["Boil it"]},
            {"step_index": 1, "title": "Add salt", "bullets": ["Add way too much salt"]}
        ]
    }
    r = client.post("/api/recipes", json=recipe_data)
    assert r.status_code in [200, 201], f"Recipe create failed: {r.text}"
    recipe_id = r.json()["id"]

    # 2. Start Session
    r = client.post("/api/cook/session/start", json={"recipe_id": recipe_id})
    assert r.status_code == 200, f"Start session failed: {r.text}"
    session_id = r.json()["id"]

    # 3. Preview Adjustment (Too Salty on step 1)
    r = client.post(f"/api/cook/session/{session_id}/adjust/preview", json={
        "step_index": 1,
        "kind": "too_salty"
    })
    assert r.status_code == 200, f"Preview failed: {r.text}"
    data = r.json()
    
    assert data["adjustment"]["kind"] == "too_salty"
    # Logic in generator ensures this bullet
    bullets_text = " ".join(data["adjustment"]["bullets"])
    assert "salt" in bullets_text or "dilute" in bullets_text
    
    # Check updated steps preview
    steps = data["steps_preview"]
    assert steps[1]["title"].startswith("Fix: Too Salty")
    assert len(steps[1]["bullets"]) >= 1

    # 4. Apply Adjustment
    adjustment_payload = {
        "adjustment_id": data["adjustment"]["id"],
        "step_index": 1,
        "steps_override": steps,
        "adjustment": data["adjustment"]
    }
    
    r = client.post(f"/api/cook/session/{session_id}/adjust/apply", json=adjustment_payload)
    assert r.status_code == 200, f"Apply failed: {r.text}"
    session_data = r.json()
    
    # Check persistence
    assert session_data["steps_override"] is not None
    assert session_data["steps_override"][1]["title"] == steps[1]["title"]
    
    # Check log
    assert len(session_data["adjustments_log"]) == 1
    assert session_data["adjustments_log"][0]["kind"] == "too_salty"
    
    # 5. Verify via session fetch
    r = client.get(f"/api/cook/session/active?recipe_id={recipe_id}")
    assert r.status_code == 200
    fetched_session = r.json()
    assert fetched_session["steps_override"][1]["title"] == steps[1]["title"]

def test_cook_adjust_missing_step(client, db_session, workspace):
    # Setup Recipe
    r = client.post("/api/recipes", json={"title": "Test", "steps": []})
    recipe_id = r.json()["id"]
    r = client.post("/api/cook/session/start", json={"recipe_id": recipe_id})
    session_id = r.json()["id"]
    
    # Request invalid step
    r = client.post(f"/api/cook/session/{session_id}/adjust/preview", json={
        "step_index": 99,
        "kind": "burning"
    })
    assert r.status_code == 404
