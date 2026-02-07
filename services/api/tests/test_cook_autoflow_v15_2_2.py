import pytest
from datetime import datetime, timedelta
from app.models import Recipe, RecipeStep, CookSession
from app.services.cook_autoflow import cook_autoflow
from app.schemas import AutoflowRequest, AutoflowClientState

@pytest.fixture
def sample_recipe(db_session):
    recipe = Recipe(title="Autoflow Pasta", workspace_id="default")
    db_session.add(recipe)
    db_session.commit()
    
    steps = [
        RecipeStep(recipe_id=recipe.id, step_index=0, title="Prep", bullets=["Chop onions", "Mince garlic"]),
        RecipeStep(recipe_id=recipe.id, step_index=1, title="Cook", bullets=["Boil water"], minutes_est=10),
        RecipeStep(recipe_id=recipe.id, step_index=2, title="Finish", bullets=["Drain", "Serve"], minutes_est=0)
    ]
    for s in steps:
        db_session.add(s)
    db_session.commit()
    return recipe

@pytest.fixture
def sample_session(db_session, sample_recipe):
    session = CookSession(
        id="autoflow_sess_1",
        recipe_id=sample_recipe.id,
        workspace_id="default",
        status="active",
        current_step_index=0,
        timers={}
    )
    db_session.add(session)
    db_session.commit()
    return session

@pytest.mark.asyncio
async def test_autoflow_initial_state(db_session, sample_session, sample_recipe):
    """Test standard initial state (heuristic)."""
    # Step 0: Prep (no time). No bullets checked.
    req = AutoflowRequest(
        step_index=0,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=[], active_timer_ids=[])
    )
    
    resp = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    # Should be empty or simple next if no complex logic applies
    # Heuristics currently don't suggest anything if no bullets checked and no timer needed
    assert len(resp.suggestions) == 0
    assert resp.source == "heuristic"

@pytest.mark.asyncio
async def test_autoflow_suggest_timer(db_session, sample_session, sample_recipe):
    """Test timer suggestion heuristic."""
    # Step 1: Cook (10 min).
    req = AutoflowRequest(
        step_index=1,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=["s1.b0"], active_timer_ids=[])
    )
    
    # User checked a bullet ("Boil water"), step has 10 min est.
    # Should suggest timer.
    resp = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    assert len(resp.suggestions) > 0
    sug = resp.suggestions[0]
    assert sug.type == "start_timer"
    assert sug.action.op == "create_timer"
    assert sug.action.payload["minutes"] == 10

@pytest.mark.asyncio
async def test_autoflow_timer_running_suppress_suggestion(db_session, sample_session, sample_recipe):
    """Test that running timer suppresses 'Start Timer' suggestion."""
    # Add running timer to session
    sample_session.timers = {
        "t1": {
            "label": "Boil", 
            "duration_sec": 600, 
            "state": "running", 
            "step_index": 1, 
            "created_at": datetime.now().isoformat()
        }
    }
    db_session.commit()
    
    req = AutoflowRequest(
        step_index=1,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=["s1.b0"], active_timer_ids=["t1"])
    )
    
    resp = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    # Should NOT suggest start timer.
    # Might suggest "Review next step" (prep_next)
    timer_suggestions = [s for s in resp.suggestions if s.type == "start_timer"]
    assert len(timer_suggestions) == 0
    
    prep_suggestions = [s for s in resp.suggestions if s.type == "prep_next"]
    assert len(prep_suggestions) > 0

@pytest.mark.asyncio
async def test_autoflow_completion_logic(db_session, sample_session, sample_recipe):
    """Test 'Mark Complete' valid/invalid scenarios."""
    
    # Scene: Step 1 (Cook 10m).
    
    # Case A: Bullets done, but Timer NOT finished (and not even started/registered in session properly for finished check).
    req = AutoflowRequest(
        step_index=1,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=["s1.b0"], active_timer_ids=[])
    )
    resp = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    # Timer required (minutes_est=10) but no finished timer found.
    # Should NOT suggest complete.
    complete_sugs = [s for s in resp.suggestions if s.type == "complete_step"]
    assert len(complete_sugs) == 0

    # Case B: Bullets done AND Timer Finished.
    sample_session.timers = {
        "t1": {
            "label": "Boil", 
            "duration_sec": 600, 
            "state": "finished", 
            "step_index": 1, 
            "created_at": datetime.now().isoformat() 
        }
    }
    sample_session.state_version += 1
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(sample_session, "timers")
    db_session.commit()
    
    print(f"DEBUG: Session Timers: {sample_session.timers}")

    req = AutoflowRequest(
        step_index=1,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=["s1.b0"], active_timer_ids=[])
    )
    resp = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    # Should suggest complete
    complete_sugs = [s for s in resp.suggestions if s.type == "complete_step"]
    assert len(complete_sugs) > 0
    assert complete_sugs[0].action.op == "navigate_step"

@pytest.mark.asyncio
async def test_autoflow_caching(db_session, sample_session, sample_recipe):
    """Test that short-term caching key works."""
    req = AutoflowRequest(
        step_index=1,
        mode="quick",
        client_state=AutoflowClientState(checked_keys=["s1.b0"], active_timer_ids=[])
    )
    
    # First call
    resp1 = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    # Second call (immediate)
    resp2 = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    
    assert resp1.autoflow_id == resp2.autoflow_id  # ID should be same if cached
    
    # Change state version to invalidate cache
    sample_session.state_version += 1
    
    resp3 = await cook_autoflow.get_next_best_action(sample_session, sample_recipe, req)
    assert resp3.autoflow_id != resp1.autoflow_id
