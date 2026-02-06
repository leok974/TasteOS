from unittest.mock import MagicMock, patch
from app.services.ai_service import AIService, SubstitutionSuggestion

def test_substitute_heuristic_fallback_when_ai_fails():
    # Setup Service in "gemini" mode
    service = AIService()
    service.mode = "gemini"
    
    # Mock ai_client to return None (failure)
    with patch("app.services.ai_service.ai_client") as mock_client:
        mock_client.generate_content_sync.return_value = None
        
        result = service.suggest_substitute(
            ingredient="Buttermilk",
            pantry_items=["Milk", "Vinegar"],
            context="Pancakes"
        )
        
        # Should fall back to heuristic
        assert result.source == "heuristic"
        # Since it's buttermilk + milk/vinegar in pantry, heuristic logic matches
        assert result.impact == "exact"
        assert result.confidence == "high"

def test_substitute_use_ai_when_available():
    # Setup Service in "gemini" mode
    service = AIService()
    service.mode = "gemini"
    
    # Expected AI Result
    ai_result = SubstitutionSuggestion(
        substitute="Yogurt watered down",
        instruction="Mix 3/4 cup yogurt with 1/4 cup water",
        confidence="high",
        impact="close",
        source="ai"
    )
    
    # Mock ai_client to return Valid Result
    with patch("app.services.ai_service.ai_client") as mock_client:
        mock_client.generate_content_sync.return_value = ai_result
        
        result = service.suggest_substitute(
            ingredient="Buttermilk",
            pantry_items=["Yogurt"],
            context="Pancakes"
        )
        
        # Should use AI result
        assert result.source == "ai"
        assert result.substitute == "Yogurt watered down"

def test_substitute_force_mock_mode():
    # Setup Service in "mock" mode
    service = AIService()
    service.mode = "mock"
    
    with patch("app.services.ai_service.ai_client") as mock_client:
        service.suggest_substitute("Buttermilk", [], "Baking")
        
        # Should NOT call AI client
        mock_client.generate_content_sync.assert_not_called()
