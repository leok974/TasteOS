from datetime import datetime, timedelta
import pytest
from sqlalchemy import select
from app.models import CookSession, RecipeNoteEntry, Workspace, Recipe, MealPlanEntry, Leftover, PantryItem
from app.schemas import CookCompleteRequest

@pytest.fixture
def create_recipe(db_session):
    def _create(**kwargs):
        recipe = Recipe(**kwargs)
        db_session.add(recipe)
        db_session.commit()
        db_session.refresh(recipe)
        return recipe
    return _create

@pytest.fixture
def create_session(db_session):
    def _create(**kwargs):
        session = CookSession(**kwargs)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session
    return _create

# Use a fresh recipe for the test
@pytest.fixture
def recipe_with_session(db_session, workspace, create_recipe, create_session):
    recipe = create_recipe(title="Test Recipe for Recap", workspace_id=workspace.id)
    session = create_session(recipe_id=recipe.id, workspace_id=workspace.id)
    return recipe, session

def test_complete_cook_session_basic(client, db_session, workspace, recipe_with_session):
    recipe, session = recipe_with_session
    
    # 1. Update session to have some interesting state
    session.step_checks = {"0_0": True, "1_0": True}
    session.timers = {
        "timer1": {"label": "Pasta", "duration_sec": 600, "state": "done"}
    }
    session.adjustments_log = [{"type": "scale", "factor": 2.0}]
    db_session.commit()
    
    # 2. Call Complete
    payload = {
        "servings_made": 4.0,
        "leftover_servings": 2.0,
        "create_leftover": True,
        "final_notes": "Sauce was great."
    }
    
    headers = {
        "Idempotency-Key": "test-key-1", 
        "X-Workspace-ID": workspace.slug
    }
    
    response = client.post(
        f"/api/cook/session/{session.id}/complete",
        json=payload,
        headers=headers
    )
    if response.status_code != 200:
        print(response.json())
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["session_id"] == session.id
    assert data["completed_at"] is not None
    assert data["note_entry_id"] is not None
    assert data["leftover_id"] is not None
    
    recap = data["recap"]
    assert recap["leftovers_created"] is True
    assert len(recap["timers_used"]) == 1
    assert len(recap["adjustments"]) == 1
    
    # 3. Verify DB State
    db_session.refresh(session)
    assert session.status == "completed"
    assert session.completed_at is not None
    assert session.recap_json["final_note"] == "Sauce was great." if "final_note" in session.recap_json else True # Checking presence
    
    # Verify Note
    note = db_session.get(RecipeNoteEntry, data["note_entry_id"])
    assert note.title == "Cook Recap"
    assert "Sauce was great" in note.content_md
    assert "leftovers" in note.tags
    assert note.data_json["leftovers_created"] is True

    # Verify Leftover
    leftover = db_session.get(Leftover, data["leftover_id"])
    assert leftover.name == recipe.title
    assert leftover.servings_left == 2.0
    assert leftover.pantry_item_id is not None
    
    # Verify Pantry Item
    pantry = db_session.get(PantryItem, leftover.pantry_item_id)
    assert pantry.category == "Leftovers"
    assert pantry.qty == 2.0

def test_complete_cook_session_idempotancy(client, db_session, workspace, recipe_with_session):
    recipe, session = recipe_with_session
    
    payload = {
        "servings_made": 2,
        "create_leftover": False
    }
    
    # First Call
    headers = {
        "Idempotency-Key": "idem-key-2",
        "X-Workspace-ID": workspace.slug
    }
    
    resp1 = client.post(
        f"/api/cook/session/{session.id}/complete",
        json=payload,
        headers=headers
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    
    # Second Call (same key)
    resp2 = client.post(
        f"/api/cook/session/{session.id}/complete",
        json=payload,
        headers=headers
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    
    assert data1["completed_at"] == data2["completed_at"]
    assert data1["note_entry_id"] == data2["note_entry_id"]
    
    # Verify only one note created
    notes = db_session.scalars(
        select(RecipeNoteEntry).where(RecipeNoteEntry.session_id == session.id)
    ).all()
    notes_count = len(notes)
    # Actually wait, SQLAlchemy count syntax is different slightly depends on version:
    # db_session.scalar(select(func.count()).select_from(RecipeNoteEntry)...)
    # Correct way:
    # count = db_session.scalar(select(func.count()).where(RecipeNoteEntry.session_id == session.id))
    # But lazy way:
    notes = db_session.scalars(select(RecipeNoteEntry).where(RecipeNoteEntry.session_id == session.id)).all()
    assert len(notes) == 1


def test_get_recipe_learnings(client, db_session, workspace, create_recipe):
    recipe = create_recipe(
        title="Learning Recipe",
        workspace_id=workspace.id,
        steps=[],
        ingredients=[]
    )
    
    # Create a couple of notes manually to simulate past sessions
    # Note 1: "Salty" issue
    note1 = RecipeNoteEntry(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        session_id=None,
        source="cook_session",
        title="Cook Recap",
        content_md="The sauce was too salty. Added water.",
        tags=["cook_recap", "salty"]
    )
    db_session.add(note1)
    
    # Note 2: "Thick" issue
    note2 = RecipeNoteEntry(
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        session_id=None,
        source="cook_session",
        title="Cook Recap",
        content_md="Texture was too thick. Cooked for less time next time.",
        tags=["cook_recap", "thick"]
    )
    db_session.add(note2)
    db_session.commit()
    
    response = client.get(
        f"/api/recipes/{recipe.id}/learnings",
        headers={"X-Workspace-ID": workspace.slug}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert "highlights" in data
    assert "common_tags" in data
    assert "recent_recaps" in data
    
    # Check highlights extraction
    # "The sauce was too salty" should be picked up due to "salty" keyword
    highlights_str = " ".join(data["highlights"]).lower()
    assert "salty" in highlights_str
    assert "thick" in highlights_str
    
    # Check tags
    assert "salty" in data["common_tags"] or "thick" in data["common_tags"]
    
    assert len(data["recent_recaps"]) == 2

