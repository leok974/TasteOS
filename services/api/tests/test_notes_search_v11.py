import pytest
from tests.conftest import TestingSessionLocal
from app.models import Recipe, RecipeNoteEntry, Workspace
from datetime import datetime, timedelta

@pytest.fixture
def db(setup_database):
    session = TestingSessionLocal()
    
    # Ensure tables exist (redundant but safe)
    from app.db import Base, engine
    Base.metadata.create_all(bind=engine)
    
    yield session
    session.close()

def test_notes_search_workflow(client, db):
    # 1. Setup Data
    workspace_id = "ws-default"
    
    # Create workspace
    db.add(Workspace(id=workspace_id, name="Default", created_at=datetime.now()))
    db.commit()
    
    recipe_id = "test-recipe-123"
    
    # Create Recipe
    db.add(Recipe(id=recipe_id, workspace_id=workspace_id, title="Test", url="http://x.com", steps=[], ingredients=[]))
    # Note 1: Air Fryer, Good
    db.add(RecipeNoteEntry(
        workspace_id=workspace_id,
        recipe_id=recipe_id,
        source="manual",
        title="Air Fryer Attempt",
        content_md="Cooked in the air fryer using default settings. Good result.",
        tags=["air_fryer", "good"],
        created_at=datetime.now()
    ))
    
    # Note 2: Oven, too salty
    db.add(RecipeNoteEntry(
        workspace_id=workspace_id,
        recipe_id=recipe_id,
        source="manual",
        title="Oven Attempt",
        content_md="Used the oven. It was too salty.",
        tags=["oven", "too_salty"],
        created_at=datetime.now() - timedelta(days=1)
    ))
    
    # Note 3: Air Fryer, too salty
    db.add(RecipeNoteEntry(
        workspace_id=workspace_id,
        recipe_id=recipe_id,
        source="manual",
        title="Another Air Fryer",
        content_md="Air fryer again. Still too salty.",
        tags=["air_fryer", "too_salty"],
        created_at=datetime.now() - timedelta(days=2)
    ))
    db.commit()
    
    # 2. Test Search by Text
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?q=salty")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 2
    assert "too salty" in data['items'][0]['content_md'] or "too salty" in data['items'][0]['title']

    # 3. Test Filter by Tag
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?tags=air_fryer")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 2 # Note 1 and 3

    # 4. Test Filter by Multiple Tags (AND)
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?tags=air_fryer&tags=too_salty")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 1 # Note 3 only
    assert data['items'][0]['title'] == "Another Air Fryer"

    # 5. Test Tags Aggregation
    resp = client.get(f"/api/recipes/{recipe_id}/notes/tags")
    assert resp.status_code == 200
    tags = resp.json()['tags']
    # Expect: air_fryer: 2, too_salty: 2, oven: 1, good: 1
    tag_map = {t['tag']: t['count'] for t in tags}
    assert tag_map['air_fryer'] == 2
    assert tag_map['oven'] == 1

    # Note 1: Air Fryer, Good
    db.add(RecipeNoteEntry(
        workspace_id=recipe['workspace_id'],
        recipe_id=recipe_id,
        source="manual",
        title="Air Fryer Attempt",
        content_md="Cooked in the air fryer using default settings. Good result.",
        tags=["air_fryer", "good"],
        created_at=datetime.now()
    ))
    
    # Note 2: Oven, too salty
    db.add(RecipeNoteEntry(
        workspace_id=recipe['workspace_id'],
        recipe_id=recipe_id,
        source="manual",
        title="Oven Attempt",
        content_md="Used the oven. It was too salty.",
        tags=["oven", "too_salty"],
        created_at=datetime.now() - timedelta(days=1)
    ))
    
    # Note 3: Air Fryer, too salty
    db.add(RecipeNoteEntry(
        workspace_id=recipe['workspace_id'],
        recipe_id=recipe_id,
        source="manual",
        title="Another Air Fryer",
        content_md="Air fryer again. Still too salty.",
        tags=["air_fryer", "too_salty"],
        created_at=datetime.now() - timedelta(days=2)
    ))
    db.commit()
    
    # 2. Test Search by Text
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?q=salty")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 2
    assert "too salty" in data['items'][0]['content_md'] or "too salty" in data['items'][0]['title']

    # 3. Test Filter by Tag
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?tags=air_fryer")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 2 # Note 1 and 3

    # 4. Test Filter by Multiple Tags (AND)
    resp = client.get(f"/api/recipes/{recipe_id}/notes/search?tags=air_fryer&tags=too_salty")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['items']) == 1 # Note 3 only
    assert data['items'][0]['title'] == "Another Air Fryer"

    # 5. Test Tags Aggregation
    resp = client.get(f"/api/recipes/{recipe_id}/notes/tags")
    assert resp.status_code == 200
    tags = resp.json()['tags']
    # Expect: air_fryer: 2, too_salty: 2, oven: 1, good: 1
    tag_map = {t['tag']: t['count'] for t in tags}
    assert tag_map['air_fryer'] == 2
    assert tag_map['oven'] == 1
