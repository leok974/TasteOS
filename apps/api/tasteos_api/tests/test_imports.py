"""
Tests for recipe import endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tasteos_api.main import app


@pytest.fixture
def mock_import_from_url():
    """Mock the recipe_importer.import_from_url function."""
    with patch('tasteos_api.routers.imports.recipe_importer.import_from_url') as mock:
        mock.return_value = {
            "title": "Test Recipe",
            "description": "A delicious test recipe",
            "servings": 4,
            "prep_time": 15,
            "cook_time": 30,
            "difficulty": "easy",
            "cuisine": "italian",
            "tags": ["pasta", "dinner"],
            "ingredients": [
                {"item": "pasta", "amount": "1 lb", "notes": None},
                {"item": "tomato sauce", "amount": "2 cups", "notes": None}
            ],
            "instructions": [
                {"step": 1, "text": "Boil water"},
                {"step": 2, "text": "Cook pasta"}
            ],
            "nutrition": None,
            "images": [],
            "source": {"url": "https://example.com/recipe"}
        }
        yield mock


@pytest.fixture
def mock_import_from_image():
    """Mock the recipe_importer.import_from_image function."""
    with patch('tasteos_api.routers.imports.recipe_importer.import_from_image') as mock:
        mock.return_value = {
            "title": "Recipe from Image",
            "description": "Imported from photo",
            "servings": 4,
            "prep_time": 20,
            "cook_time": 25,
            "difficulty": "medium",
            "cuisine": "general",
            "tags": ["imported"],
            "ingredients": [
                {"item": "ingredient 1", "amount": "1 cup", "notes": None}
            ],
            "instructions": [
                {"step": 1, "text": "Follow OCR instructions"}
            ],
            "nutrition": None,
            "images": [],
            "source": None
        }
        yield mock


@pytest.mark.asyncio
async def test_import_from_url(mock_import_from_url, auth_headers):
    """Test importing a recipe from a URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/url",
            json={"url": "https://example.com/test-recipe"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "recipe" in data
        assert data["recipe"]["title"] == "Test Recipe"
        assert data["recipe"]["cuisine"] == "italian"
        assert len(data["recipe"]["ingredients"]) == 2
        assert len(data["recipe"]["instructions"]) == 2

        # Verify the importer was called
        mock_import_from_url.assert_called_once_with("https://example.com/test-recipe")


@pytest.mark.asyncio
async def test_import_from_url_unauthorized():
    """Test that import from URL requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/url",
            json={"url": "https://example.com/test-recipe"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_from_url_invalid_url(auth_headers):
    """Test import with invalid URL format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/url",
            json={"url": "not-a-valid-url"},
            headers=auth_headers
        )

        # Should fail validation
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_from_image(mock_import_from_image, auth_headers):
    """Test importing a recipe from an image."""
    # Create a fake image file
    image_data = b"fake-image-bytes"
    files = {"image": ("recipe.jpg", image_data, "image/jpeg")}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/image",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "recipe" in data
        assert data["recipe"]["title"] == "Recipe from Image"
        assert "imported" in data["recipe"]["tags"]

        # Verify the importer was called
        mock_import_from_image.assert_called_once()


@pytest.mark.asyncio
async def test_import_from_image_unauthorized():
    """Test that import from image requires authentication."""
    image_data = b"fake-image-bytes"
    files = {"image": ("recipe.jpg", image_data, "image/jpeg")}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/image",
            files=files
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_from_image_wrong_type(auth_headers):
    """Test that non-image files are rejected."""
    text_data = b"this is not an image"
    files = {"image": ("document.txt", text_data, "text/plain")}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/imports/image",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()
