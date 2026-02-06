from unittest.mock import MagicMock, patch
from app.services.ai_service import AIService, MacroAnalysis

def test_macros_heuristic_fallback_when_ai_fails():
    # Setup Service in "gemini" mode
    service = AIService()
    service.mode = "gemini"
    
    # Mock ai_client to return None (failure)
    with patch("app.services.ai_service.ai_client") as mock_client:
        mock_client.generate_content_sync.return_value = None
        
        result = service.summarize_macros(
            title="Grilled Chicken Salad",
            ingredients=["Chicken", "Lettuce", "Tomatoes"]
        )
        
        # Should fall back to heuristic
        assert result.source == "heuristic"
        # Since it's a salad, heuristic Logic
        assert result.confidence == "medium"
        assert "low-calorie" in result.tags

def test_macros_use_ai_when_available():
    # Setup Service in "gemini" mode
    service = AIService()
    service.mode = "gemini"
    
    # Expected AI Result
    ai_result = MacroAnalysis(
        calories_range={"min": 300, "max": 400},
        protein_range={"min": 25, "max": 30},
        confidence="high",
        disclaimer="AI generated",
        tags=["ai-tag"],
        source="ai"
    )
    
    # Mock ai_client to return Valid Result
    with patch("app.services.ai_service.ai_client") as mock_client:
        mock_client.generate_content_sync.return_value = ai_result
        
        result = service.summarize_macros(
            title="Grilled Chicken Salad",
            ingredients=["Chicken", "Lettuce", "Tomatoes"]
        )
        
        # Should use AI result
        assert result.source == "ai"
        assert result.tags == ["ai-tag"]
        assert result.confidence == "high"

def test_macros_force_mock_mode():
    # Setup Service in "mock" mode
    service = AIService()
    service.mode = "mock"
    
    with patch("app.services.ai_service.ai_client") as mock_client:
        service.summarize_macros("Steak", ["Beef"])
        
        # Should NOT call AI client
        mock_client.generate_content_sync.assert_not_called()

