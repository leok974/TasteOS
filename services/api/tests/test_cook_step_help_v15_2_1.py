from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from app.services.cook_assist_help import CookAssistHelpService, CookStepHelpAIResponse, SafetyFlags, TimerSuggestion, CookStepHelpRequest

@pytest.fixture
def service():
    return CookAssistHelpService()

@pytest.mark.asyncio
async def test_step_help_idempotency_id(service):
    """Verify help_id is generated and returned"""
    # Mock AI response
    ai_resp = CookStepHelpAIResponse(
        answer_md="Res",
        bullets=[],
        confidence="high",
        safety=SafetyFlags(contains_food_safety=False, allergens=[]),
        timer_suggestions=[] # List now required in internal schema
    )
    
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "sess1"
    mock_session.workspace_id = "ws1"
    mock_session.recipe_id = "r1"
    mock_session.state_version = 1
    
    mock_recipe = MagicMock()
    mock_recipe.id = "r1"
    mock_recipe.title = "Recipe"
    mock_recipe.steps = []
    mock_recipe.ingredients = []
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_session, mock_recipe]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [] 

    with patch("app.services.cook_assist_help.ai_client") as mock_client:
        mock_client.is_available.return_value = True
        mock_client.generate_structured = AsyncMock(return_value=ai_resp)
        
        req = CookStepHelpRequest(step_index=0, question="Is it done?")
        res = await service.get_step_help(mock_db, "sess1", req, "ws1")
        
        assert res.help_id is not None
        assert len(res.help_id) > 10 # Hash check

@pytest.mark.asyncio
async def test_step_help_context_timers(service):
    """Verify active timers are injected into prompt"""
    
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "sess1"
    mock_session.recipe_id = "r1"
    mock_session.workspace_id = "ws1"
    mock_session.state_version = 1
    # Add active timers
    mock_session.timers = {
        "t1": {"label": "Pasta", "duration_sec": 60, "status": "running"}
    }
    
    mock_recipe = MagicMock()
    mock_recipe.id = "r1"
    mock_recipe.title = "Pasta"
    mock_recipe.steps = []
    mock_recipe.ingredients = []
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_session, mock_recipe]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    
    with patch("app.services.cook_assist_help.ai_client") as mock_client:
        mock_client.is_available.return_value = True
        mock_client.generate_structured = AsyncMock(return_value=None) # We just want to check prompt
        
        req = CookStepHelpRequest(step_index=0, question="Check timers")
        try:
            await service.get_step_help(mock_db, "sess1", req, "ws1")
        except AttributeError: 
            pass # Since we return None for AI resp, falback might trigger, but we care about call args
        
        # Check call args
        call_args = mock_client.generate_structured.call_args
        assert call_args is not None
        prompt = call_args.kwargs['prompt']
        
        assert "ACTIVE TIMERS" in prompt
        assert "Pasta: 60s remaining" in prompt
