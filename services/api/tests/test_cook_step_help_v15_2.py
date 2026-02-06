from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from app.services.cook_assist_help import CookAssistHelpService, CookStepHelpAIResponse, SafetyFlags, TimerSuggestion, CookStepHelpRequest

@pytest.fixture
def service():
    return CookAssistHelpService()

@pytest.mark.asyncio
async def test_step_help_success_ai(service):
    # Mock AI response
    ai_resp = CookStepHelpAIResponse(
        answer_md="Check **doneness**.",
        bullets=["Look for gold color", "Internal temp 165F"],
        confidence="high",
        safety=SafetyFlags(contains_food_safety=True, allergens=[]),
        timer_suggestion=TimerSuggestion(label="Rest chicken", seconds=300, rationale="Juicier meat")
    )
    
    # Mock dependencies
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.recipe_id = "recipe1"
    mock_recipe = MagicMock()
    mock_recipe.title = "Roast Chicken"
    mock_recipe.steps = [{"step_index": 0, "instruction": "Cook it"}]
    mock_recipe.ingredients = []
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_session, mock_recipe]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [] # Notes
    
    with patch("app.services.cook_assist_help.ai_client") as mock_client:
        mock_client.is_available.return_value = True
        mock_client.generate_structured = AsyncMock(return_value=ai_resp)
        
        req = CookStepHelpRequest(step_index=0, question="Is it done?")
        res = await service.get_step_help(mock_db, "sess1", req, "ws1")
        
        assert res.source == "ai"
        assert len(res.bullets) == 2
        assert res.timer_suggestion.seconds == 300
        assert res.safety.contains_food_safety is True

@pytest.mark.asyncio
async def test_step_help_fallback_heuristic(service):
    # Mock failure
    mock_db = MagicMock()
    # Same setup
    mock_recipe = MagicMock()
    mock_recipe.title = "Recipe"
    mock_recipe.ingredients = []  # Empty list is JSON serializable
    mock_recipe.steps = [{"step_index": 0, "instruction": "Cook"}] # Serializable
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [MagicMock(recipe_id="r1"), mock_recipe]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    
    with patch("app.services.cook_assist_help.ai_client") as mock_client:
        mock_client.is_available.return_value = True
        mock_client.generate_structured = AsyncMock(return_value=None) # Fails
        
        req = CookStepHelpRequest(step_index=0, question="Help?")
        res = await service.get_step_help(mock_db, "sess1", req, "ws1")
        
        assert res.source == "heuristic"
        assert res.confidence == "low"
        assert res.timer_suggestion is None
