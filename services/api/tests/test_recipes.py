"""Tests for TasteOS API.

Tests cover:
- Workspace resolution
- Recipe CRUD with steps
- Dev seed endpoint
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import Workspace, Recipe, RecipeStep
from app.deps import get_workspace


# --- Tests ---


def test_ready_endpoint(client):
    """Ready endpoint returns ok."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_seed_creates_workspace_and_recipes(client):
    """Seed endpoint creates local workspace and sample recipes."""
    response = client.post("/api/dev/seed")
    assert response.status_code == 200
    
    data = response.json()
    assert data["workspace"]["slug"] == "local"
    assert data["recipes_created"] >= 1
    assert "Created" in data["message"]


def test_seed_is_idempotent(client):
    """Running seed multiple times doesn't create duplicates."""
    response1 = client.post("/api/dev/seed")
    assert response1.status_code == 200
    count1 = response1.json()["recipes_created"]
    
    response2 = client.post("/api/dev/seed")
    assert response2.status_code == 200
    count2 = response2.json()["recipes_created"]
    
    # Second run should create 0 new recipes
    assert count2 == 0


def test_list_recipes_empty_without_workspace(client):
    """List recipes returns 404 when no workspace exists."""
    response = client.get("/api/recipes")
    assert response.status_code == 404
    assert "No workspace found" in response.json()["detail"]


def test_list_recipes_after_seed(client):
    """List recipes returns seeded data."""
    # Seed first
    client.post("/api/dev/seed")
    
    response = client.get("/api/recipes")
    assert response.status_code == 200
    
    recipes = response.json()
    assert len(recipes) >= 1
    assert all("id" in r for r in recipes)
    assert all("title" in r for r in recipes)


def test_create_recipe_with_steps(client):
    """Create recipe with nested steps."""
    # Seed workspace first
    client.post("/api/dev/seed")
    
    payload = {
        "title": "Test Recipe",
        "cuisines": ["Italian"],
        "tags": ["quick", "easy"],
        "servings": 4,
        "time_minutes": 30,
        "notes": "A test recipe",
        "steps": [
            {
                "step_index": 0,
                "title": "Prep ingredients",
                "bullets": ["Chop onions", "Mince garlic"],
                "minutes_est": 10,
            },
            {
                "step_index": 1,
                "title": "Cook",
                "bullets": ["Sauté in pan", "Add sauce"],
                "minutes_est": 15,
            },
        ],
    }
    
    response = client.post("/api/recipes", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["title"] == "Test Recipe"
    assert data["cuisines"] == ["Italian"]
    assert len(data["steps"]) == 2
    assert data["steps"][0]["title"] == "Prep ingredients"
    assert data["steps"][1]["title"] == "Cook"


def test_get_recipe_includes_steps(client):
    """Get single recipe includes all steps."""
    # Create recipe
    client.post("/api/dev/seed")
    
    # List to get an ID
    recipes = client.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]
    
    # Get single recipe
    response = client.get(f"/api/recipes/{recipe_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert "steps" in data
    assert len(data["steps"]) >= 1


def test_patch_recipe_updates_title(client):
    """Patch recipe updates scalar fields."""
    client.post("/api/dev/seed")
    recipes = client.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]
    
    response = client.patch(
        f"/api/recipes/{recipe_id}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_patch_recipe_replaces_steps(client):
    """Patch recipe with steps replaces all existing steps."""
    client.post("/api/dev/seed")
    recipes = client.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]
    
    new_steps = [
        {
            "step_index": 0,
            "title": "New Step 1",
            "bullets": ["Do this"],
            "minutes_est": 5,
        },
    ]
    
    response = client.patch(
        f"/api/recipes/{recipe_id}",
        json={"steps": new_steps},
    )
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["steps"]) == 1
    assert data["steps"][0]["title"] == "New Step 1"


def test_recipe_not_found_returns_404(client):
    """Get non-existent recipe returns 404."""
    client.post("/api/dev/seed")
    
    response = client.get("/api/recipes/nonexistent-id")
    assert response.status_code == 404


def test_search_filters_recipes(client):
    """Search parameter filters recipes by title."""
    client.post("/api/dev/seed")
    
    # Search for enchiladas
    response = client.get("/api/recipes?search=enchilada")
    assert response.status_code == 200
    
    recipes = response.json()
    # Should find at least the Salsa Verde Enchiladas
    assert any("enchilada" in r["title"].lower() for r in recipes)
