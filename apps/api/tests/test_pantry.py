"""
Tests for pantry endpoints
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from fastapi import status

from tasteos_api.models.pantry_item import PantryItem


@pytest.mark.asyncio
async def test_list_pantry_items(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test listing pantry items"""
    response = await async_client.get("/api/v1/pantry", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_add_pantry_item(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test adding a new pantry item"""
    data = {
        "name": "Chicken Breast",
        "quantity": 2.0,
        "unit": "lbs",
        "tags": ["meat", "protein"],
    }
    response = await async_client.post("/api/v1/pantry", json=data, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["name"] == "Chicken Breast"
    assert result["quantity"] == 2.0
    assert result["unit"] == "lbs"
    assert "meat" in result["tags"]


@pytest.mark.asyncio
async def test_upsert_pantry_item(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test upserting an existing pantry item updates quantity"""
    # First add
    data = {
        "name": "Eggs",
        "quantity": 6.0,
        "unit": "count",
    }
    response1 = await async_client.post("/api/v1/pantry", json=data, headers=auth_headers)
    assert response1.status_code == status.HTTP_200_OK

    # Upsert with same name
    data["quantity"] = 12.0
    response2 = await async_client.post("/api/v1/pantry", json=data, headers=auth_headers)
    assert response2.status_code == status.HTTP_200_OK
    result = response2.json()
    assert result["quantity"] == 12.0


@pytest.mark.asyncio
async def test_delete_pantry_item(async_client: AsyncClient, auth_headers: dict, test_user):
    """Test deleting a pantry item"""
    # Add item first
    data = {"name": "Milk", "quantity": 1.0, "unit": "gallon"}
    add_response = await async_client.post("/api/v1/pantry", json=data, headers=auth_headers)
    item_id = add_response.json()["id"]

    # Delete it
    response = await async_client.delete(f"/api/v1/pantry/{item_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Item deleted"


@pytest.mark.asyncio
@patch("tasteos_api.routers.pantry.pantry_agent.parse_item")
async def test_scan_pantry_item(mock_parse, async_client: AsyncClient, auth_headers: dict, test_user):
    """Test scanning/parsing a pantry item with AI"""
    mock_parse.return_value = {
        "name": "Onion",
        "quantity": 0.5,
        "unit": "count",
        "tags": ["vegetable"],
    }

    response = await async_client.post(
        "/api/v1/pantry/scan",
        params={"raw_text": "half an onion"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["name"] == "Onion"
    assert result["quantity"] == 0.5
    mock_parse.assert_called_once()


@pytest.mark.asyncio
async def test_list_pantry_unauthorized(async_client: AsyncClient):
    """Test listing pantry without authentication fails"""
    response = await async_client.get("/api/v1/pantry")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
