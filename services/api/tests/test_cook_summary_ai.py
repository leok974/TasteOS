import pytest
import os
from unittest.mock import MagicMock, patch
from app.ai.summary import polish_summary, PolishedSummary
from app.models import Recipe, CookSession
import uuid
from datetime import datetime, timezone

def test_summary_polish_logic():
    # Test valid JSON response from Gemini
    # We need to ensure get_client sees an API key
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), \
         patch("app.ai.summary.genai.Client") as MockClient:
        
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = '{"title": "Valid", "tldr": "TLDR", "bullets": ["A"], "next_time": [], "warnings": [], "confidence": 0.8}'
        mock_instance.models.generate_content.return_value = mock_response
        
        facts = {"method_key": "test"}
        result = polish_summary(facts)
        assert result.confidence == 0.8
        assert result.tldr == "TLDR"

    # Test invalid JSON fallback
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), \
         patch("app.ai.summary.genai.Client") as MockClient:
        
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = 'Broken JSON'
        mock_instance.models.generate_content.return_value = mock_response
        
        facts = {"method_key": "test"}
        result = polish_summary(facts)
        assert result.confidence == 0.4
        assert "Method: test" in result.bullets

from app.deps import get_workspace
from app.main import app

def test_notes_preview_uses_ai_result(client, workspace, db_session):
    # Override get_workspace to bypass DB lookup issues in test env
    # Note: client fixture sets overrides, so we update them
    app.dependency_overrides[get_workspace] = lambda: workspace

    # Setup Data
    r = Recipe(id=uuid.uuid4().hex, workspace_id=workspace.id, title="Test Recipe")
    db_session.add(r)
    s = CookSession(
        id=uuid.uuid4().hex,
        workspace_id=workspace.id,
        recipe_id=r.id,
        status="completed",
        servings_base=2,
        servings_target=2,
        current_step_index=0
    )
    db_session.add(s)
    db_session.commit()
    
    print(f"DEBUG: Created Session {s.id} in Workspace {workspace.id}")
    
    headers = {"X-Workspace-Id": workspace.id}
    
    # Mock polish_summary to return predictable "AI" result
    with patch("app.routers.cook.polish_summary") as mock_polish:
        mock_polish.return_value = PolishedSummary(
            title="AI Title",
            tldr="AI TLDR",
            bullets=["AI Bullet 1"],
            next_time=["AI Next Time 1"],
            warnings=[],
            confidence=0.9
        )
        
        response = client.post(
            f"/api/cook/session/{s.id}/notes/preview",
            json={
                "include": {"method": True, "adjustments": True},
                "use_ai": True,
                "style": "friendly"
            },
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"DEBUG: Response {response.status_code} - {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if AI content is in proposal
        notes = data["proposal"]["recipe_patch"]["notes_append"]
        assert "Next time:" in notes
        assert "  - AI Next Time 1" in notes
        assert "Session highlights:" in notes 
        assert "  - AI Bullet 1" in notes
        
        # Verify call args
        mock_polish.assert_called_once()
        call_kwargs = mock_polish.call_args.kwargs
        assert call_kwargs["style"] == "friendly"
