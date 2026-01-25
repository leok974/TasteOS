import pytest
from datetime import datetime, timedelta, timezone
from app.services.events import log_event
from app.services.auto_step_from_events import calculate_auto_step_from_events
from app.models import CookSession, Recipe, RecipeStep

@pytest.fixture
def recipe(db_session, workspace):
    recipe = Recipe(workspace_id=workspace.id, title="Test Recipe")
    db_session.add(recipe)
    db_session.commit()
    
    # Add steps
    for i in range(10):
        step = RecipeStep(recipe_id=recipe.id, step_index=i, title=f"Step {i}")
        db_session.add(step)
    
    db_session.commit()
    return recipe

def test_autostep_timer_start_dominance(db_session, workspace, recipe):
    # Setup session
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        current_step_index=0,
        auto_step_enabled=True,
        auto_step_mode="suggest"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    # 1. Start timer on step 4
    log_event(db=db_session, workspace_id=workspace.id, session_id=session.id, type="timer_start", 
              step_index=4, meta={"action": "start"})
    db_session.commit()
    
    # Analyze
    calculate_auto_step_from_events(session, db_session)
    
    assert session.auto_step_suggested_index == 4
    assert session.auto_step_confidence > 0.6
    assert session.auto_step_reason == "Timer started"

def test_manual_override_prevents_autojump(db_session, workspace, recipe):
    # Setup session: Auto-jump enabled
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        current_step_index=0,
        auto_step_enabled=True,
        auto_step_mode="auto_jump"
    )
    db_session.add(session)
    db_session.commit()
    
    # 1. User manual nav to step 1 (sets override for 3m)
    now = datetime.now(timezone.utc)
    session.manual_override_until = now + timedelta(minutes=3)
    
    # 2. Strong signal on step 5
    log_event(db=db_session, workspace_id=workspace.id, session_id=session.id, type="timer_start", 
              step_index=5, meta={"action": "start"})
    db_session.commit()
    
    calculate_auto_step_from_events(session, db_session, now=now)
    
    # Check suggestion is correct but NO JUMP happened
    assert session.auto_step_suggested_index == 5
    assert session.current_step_index == 0 # stayed put
    assert session.auto_step_confidence <= 0.55 # capped

def test_check_toggles_push_suggestion(db_session, workspace, recipe):
    session = CookSession(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        current_step_index=0,
        auto_step_enabled=True,
        auto_step_mode="suggest"
    )
    db_session.add(session)
    db_session.commit()

    # Toggle items on step 2
    log_event(db=db_session, workspace_id=workspace.id, session_id=session.id, type="check_step", step_index=2, meta={})
    log_event(db=db_session, workspace_id=workspace.id, session_id=session.id, type="check_step", step_index=2, meta={})
    db_session.commit()
    
    calculate_auto_step_from_events(session, db_session)
    
    assert session.auto_step_suggested_index == 2
