"""
Tests for nutrition endpoints.

Tests the GET /recipes/{id}/nutrition and GET /variants/{id}/nutrition endpoints
with mocked nutrition analyzer to avoid external API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.main import app
from tasteos_api.models.recipe import Recipe
from tasteos_api.models.variant import RecipeVariant
from tasteos_api.models.recipe_nutrition import RecipeNutrition


@pytest.fixture
def mock_analyze_recipe_macros():
    """Mock the nutrition analyzer to return consistent test data."""
    with patch('tasteos_api.routers.nutrition.nutrition_analyzer.analyze_recipe_macros') as mock:
        async def mock_analyzer(recipe_data, variant_data=None):
            # Return different values based on whether it's a variant
            if variant_data:
                return {
                    "calories": 450,
                    "protein_g": 32.0,
                    "carbs_g": 38.0,
                    "fat_g": 15.0,
                    "notes": "Higher protein, reduced cream vs base"
                }
            else:
                return {
                    "calories": 520,
                    "protein_g": 24.0,
                    "carbs_g": 45.0,
                    "fat_g": 22.0,
                    "notes": "Standard nutrition profile"
                }

        mock.side_effect = mock_analyzer
        yield mock


@pytest.mark.asyncio
async def test_get_recipe_nutrition_not_cached(
    mock_analyze_recipe_macros,
    auth_headers,
    test_recipe,
    db_session: AsyncSession
):
    """Test getting nutrition for a recipe when not cached (should calculate and cache)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/recipes/{test_recipe.id}/nutrition",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify the response structure and values
        assert data["calories"] == 520
        assert data["protein_g"] == 24.0
        assert data["carbs_g"] == 45.0
        assert data["fat_g"] == 22.0
        assert data["notes"] == "Standard nutrition profile"

        # Verify analyzer was called
        mock_analyze_recipe_macros.assert_called_once()

        # Verify it was cached in the database
        result = await db_session.execute(
            select(RecipeNutrition)
            .where(RecipeNutrition.recipe_id == test_recipe.id)
            .where(RecipeNutrition.variant_id == None)
        )
        cached = result.scalar_one_or_none()

        assert cached is not None
        assert cached.calories == 520
        assert cached.protein_g == 24.0
        assert cached.carbs_g == 45.0
        assert cached.fat_g == 22.0


@pytest.mark.asyncio
async def test_get_recipe_nutrition_cached(
    auth_headers,
    test_recipe,
    db_session: AsyncSession
):
    """Test getting nutrition for a recipe when already cached (should not recalculate)."""
    # Pre-populate the cache
    cached_nutrition = RecipeNutrition(
        recipe_id=test_recipe.id,
        variant_id=None,
        calories=600,
        protein_g=30.0,
        carbs_g=50.0,
        fat_g=25.0,
        notes="Cached nutrition data"
    )
    db_session.add(cached_nutrition)
    await db_session.commit()

    with patch('tasteos_api.routers.nutrition.nutrition_analyzer.analyze_recipe_macros') as mock_analyzer:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/recipes/{test_recipe.id}/nutrition",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Should return cached values
            assert data["calories"] == 600
            assert data["protein_g"] == 30.0
            assert data["carbs_g"] == 50.0
            assert data["fat_g"] == 25.0
            assert data["notes"] == "Cached nutrition data"

            # Analyzer should NOT have been called
            mock_analyzer.assert_not_called()


@pytest.mark.asyncio
async def test_get_variant_nutrition_not_cached(
    mock_analyze_recipe_macros,
    auth_headers,
    test_recipe,
    db_session: AsyncSession
):
    """Test getting nutrition for a variant when not cached."""
    # Create a test variant
    variant = RecipeVariant(
        recipe_id=test_recipe.id,
        title="High Protein Variant",
        description="Increased protein version",
        variant_type="dietary",
        status="pending",
        modified_ingredients='[{"item": "chicken", "amount": "2 lbs"}]',
        rationale="More protein for gains"
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/variants/{variant.id}/nutrition",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify variant nutrition values (higher protein, lower fat)
        assert data["calories"] == 450
        assert data["protein_g"] == 32.0
        assert data["carbs_g"] == 38.0
        assert data["fat_g"] == 15.0
        assert "Higher protein" in data["notes"]

        # Verify analyzer was called with variant data
        mock_analyze_recipe_macros.assert_called_once()

        # Verify it was cached
        result = await db_session.execute(
            select(RecipeNutrition)
            .where(RecipeNutrition.variant_id == variant.id)
        )
        cached = result.scalar_one_or_none()

        assert cached is not None
        assert cached.calories == 450
        assert cached.protein_g == 32.0


@pytest.mark.asyncio
async def test_get_variant_nutrition_cached(
    auth_headers,
    test_recipe,
    db_session: AsyncSession
):
    """Test getting nutrition for a variant when already cached."""
    # Create a test variant
    variant = RecipeVariant(
        recipe_id=test_recipe.id,
        title="Test Variant",
        description="Test",
        variant_type="dietary",
        status="pending",
        modified_ingredients='[{"item": "test"}]',
        rationale="Test"
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)

    # Pre-populate cache
    cached_nutrition = RecipeNutrition(
        recipe_id=test_recipe.id,
        variant_id=variant.id,
        calories=400,
        protein_g=28.0,
        carbs_g=35.0,
        fat_g=18.0,
        notes="Cached variant nutrition"
    )
    db_session.add(cached_nutrition)
    await db_session.commit()

    with patch('tasteos_api.routers.nutrition.nutrition_analyzer.analyze_recipe_macros') as mock_analyzer:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/variants/{variant.id}/nutrition",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Should return cached values
            assert data["calories"] == 400
            assert data["protein_g"] == 28.0

            # Analyzer should NOT have been called
            mock_analyzer.assert_not_called()


@pytest.mark.asyncio
async def test_get_recipe_nutrition_unauthorized(test_recipe):
    """Test that unauthorized users cannot access recipe nutrition."""
    # TODO: Implement auth validation test
    # This should return 401 when no auth headers are provided
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/recipes/{test_recipe.id}/nutrition"
        )

        # Expected behavior: 401 Unauthorized or 403 Forbidden
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_get_recipe_nutrition_not_found(auth_headers):
    """Test getting nutrition for non-existent recipe."""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/recipes/{fake_id}/nutrition",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_variant_nutrition_not_found(auth_headers):
    """Test getting nutrition for non-existent variant."""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/variants/{fake_id}/nutrition",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_nutrition_response_format(
    mock_analyze_recipe_macros,
    auth_headers,
    test_recipe
):
    """Test that nutrition response has correct format and required fields."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/recipes/{test_recipe.id}/nutrition",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["calories", "protein_g", "carbs_g", "fat_g"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify data types
        assert isinstance(data["calories"], int)
        assert isinstance(data["protein_g"], (int, float))
        assert isinstance(data["carbs_g"], (int, float))
        assert isinstance(data["fat_g"], (int, float))

        # notes is optional but should be present (can be null)
        assert "notes" in data
