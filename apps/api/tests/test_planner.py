"""
Tests for planner endpoints
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from fastapi import status
from datetime import date


@pytest.mark.asyncio
@patch("tasteos_api.routers.planner.planner_agent.generate_week_plan")
async def test_generate_meal_plan(mock_generate, async_client: AsyncClient, auth_headers: dict, test_user):
    """Test generating a meal plan"""
    mock_generate.return_value = [
        {
            "date": str(date.today()),
            "breakfast": [{"recipe_id": None, "title": "Oatmeal"}],
            "lunch": [{"recipe_id": None, "title": "Salad"}],
            "dinner": [{"recipe_id": None, "title": "Pasta"}],
            "snacks": [],
            "total_calories": 1800,
            "total_protein_g": 70,
            "total_carbs_g": 200,
            "total_fat_g": 50,
        }
    ]

    data = {
        "days": 7,
        "goals": {"calories": 2000, "protein_g": 150},
        "dietary_preferences": ["vegetarian"],
    }
    response = await async_client.post("/api/v1/planner/generate", json=data, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "plan_ids" in result
    assert len(result["plan_ids"]) > 0
    mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_get_today_plan_not_found(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test getting today's plan when none exists"""
    response = await async_client.get("/api/v1/planner/today", headers=auth_headers)
    # Should return 200 with null or 404
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_get_plan_by_id_not_found(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test getting a non-existent plan by ID"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/api/v1/planner/{fake_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("tasteos_api.routers.planner.planner_agent.generate_week_plan")
async def test_generate_plan_with_preferences(
    mock_generate, async_client: AsyncClient, auth_headers: dict, test_user
):
    """Test generating a meal plan with dietary preferences"""
    mock_generate.return_value = [
        {
            "date": str(date.today()),
            "breakfast": [{"recipe_id": None, "title": "Vegan Pancakes"}],
            "lunch": [{"recipe_id": None, "title": "Quinoa Bowl"}],
            "dinner": [{"recipe_id": None, "title": "Tofu Stir Fry"}],
            "snacks": [{"recipe_id": None, "title": "Almonds"}],
            "total_calories": 1600,
            "total_protein_g": 80,
            "total_carbs_g": 180,
            "total_fat_g": 45,
        }
    ]

    data = {
        "days": 3,
        "goals": {"calories": 1600, "protein_g": 80},
        "dietary_preferences": ["vegan", "gluten-free"],
    }
    response = await async_client.post("/api/v1/planner/generate", json=data, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["plan_ids"]) > 0

    # Check that preferences were passed to agent
    call_args = mock_generate.call_args
    assert "vegan" in call_args[1]["prefs"]
    assert "gluten-free" in call_args[1]["prefs"]


@pytest.mark.asyncio
async def test_generate_plan_unauthorized(async_client: AsyncClient):
    """Test generating a meal plan without authentication fails"""
    data = {
        "days": 7,
        "goals": {"calories": 2000, "protein_g": 150},
        "dietary_preferences": [],
    }
    response = await async_client.post("/api/v1/planner/generate", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
