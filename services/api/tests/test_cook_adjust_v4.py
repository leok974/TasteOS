from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import CookSession, Recipe, Workspace, RecipeStep
from app.services import cook_adjustments
from app.schemas import CookAdjustment

@pytest.fixture
def mock_gemini_client():
    with patch("app.services.cook_adjustments.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def recipe(db_session: Session, workspace: Workspace):
    """Create a test recipe."""
    r = Recipe(
        id="recipe-123",
        workspace_id=workspace.id,
        title="Test Recipe",
        steps=[
            RecipeStep(step_index=0, title="Step 1", bullets=["Do this"], minutes_est=5),
            RecipeStep(step_index=1, title="Step 2", bullets=["Do that"], minutes_est=10)
        ]
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r

def test_adjustment_rules_basic():
    """Test standard rule-based adjustment."""
    adj = cook_adjustments.generate_adjustment(
        session_method_key=None,
        step_index=0,
        original_step={"title": "Test", "bullets": ["Do stuff"]},
        kind="too_salty"
    )
    assert adj.kind == "too_salty"
    assert "dilute" in adj.bullets[0] or "dilute" in adj.bullets[1]
    assert adj.source == "rules"
    assert adj.confidence >= 0.8

def test_adjustment_rules_method_aware():
    """Test method-specific rule refinements."""
    adj = cook_adjustments.generate_adjustment(
        session_method_key="air_fryer",
        step_index=0,
        original_step={"title": "Test", "bullets": ["Do stuff"]},
        kind="no_browning"
    )
    # Check for Air Fryer specific advice
    assert any("Shake the basket" in b for b in adj.bullets)

def test_adjustment_ai_fallback(mock_gemini_client):
    """Test AI fallback for unknown kinds."""
    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = '{"title": "AI Fix", "bullets": ["AI step 1"], "warnings": []}'
    mock_gemini_client.models.generate_content.return_value = mock_response

    adj = cook_adjustments.generate_adjustment(
        session_method_key="standard",
        step_index=0,
        original_step={"title": "Weird Step", "bullets": ["Do weird stuff"]},
        kind="strange_texture"
    )
    
    assert adj.kind == "strange_texture"
    assert adj.title == "AI Fix"
    assert adj.bullets == ["AI step 1"]
    assert adj.source == "ai_gemini"
    assert adj.confidence == 0.9

def test_api_adjustment_flow(client: TestClient, db_session: Session, workspace: Workspace, recipe: Recipe):
    # 1. Start Session
    resp = client.post(
        f"/api/cook/session/start", 
        json={"recipe_id": recipe.id, "servings": 2},
        headers={"Idempotency-Key": "test-start-123"}
    )
    assert resp.status_code == 200, f"Start failed: {resp.text}"
    session_id = resp.json()["id"]

    # 2. Preview Adjustment (No idempotency needed usually, but safe to verify)
    preview_req = {
        "step_index": 0,
        "kind": "too_salty",
        "context": {}
    }
    resp = client.post(f"/api/cook/session/{session_id}/adjust/preview", json=preview_req)
    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()
    assert data["adjustment"]["kind"] == "too_salty"
    assert data["steps_preview"][0]["title"] == "Fix: Too Salty"
    
    adjustment_obj = data["adjustment"]
    steps_preview = data["steps_preview"]

    # 3. Apply Adjustment
    apply_req = {
        "adjustment_id": adjustment_obj["id"],
        "step_index": 0,
        "steps_override": steps_preview,
        "adjustment": adjustment_obj
    }
    resp = client.post(
        f"/api/cook/session/{session_id}/adjust/apply", 
        json=apply_req,
        headers={"Idempotency-Key": "test-apply-456"}
    )
    assert resp.status_code == 200, f"Apply failed: {resp.text}"
    assert resp.json()["steps_override"][0]["title"] == "Fix: Too Salty"
    
    # Verify DB
    session = db_session.query(CookSession).filter_by(id=session_id).first()
    assert len(session.adjustments_log) == 1
    assert session.adjustments_log[0]["kind"] == "too_salty"
    assert session.adjustments_log[0]["applied_at"] is not None

    # 4. Undo Adjustment
    print(f"DEBUG: Adjustment ID to undo: {adjustment_obj['id']}")
    print(f"DEBUG: Session Log: {session.adjustments_log}")

    undo_req = {
        "adjustment_id": adjustment_obj["id"]
    }
    resp = client.post(
        f"/api/cook/session/{session_id}/adjust/undo", 
        json=undo_req,
        headers={"Idempotency-Key": "test-undo-789"}
    )
    assert resp.status_code == 200, f"Undo failed: {resp.text}"
    
    # Reload session
    db_session.refresh(session)
    # Check if reverted
    assert session.steps_override[0]["title"] != "Fix: Too Salty"
    assert session.adjustments_log[0]["undone_at"] is not None

