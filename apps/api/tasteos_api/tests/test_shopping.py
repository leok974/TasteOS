import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_generate_shopping_list(async_client, meal_plan_seed):
    fake_list = [
        {"name": "chicken breast", "quantity": 2, "unit": "lb"},
        {"name": "spinach", "quantity": 1, "unit": "bag"}
    ]

    with patch("tasteos_api.agents.shopping_agent.plan_to_list") as mock_list:
        mock_list.return_value = fake_list

        resp = await async_client.post(
            "/api/v1/shopping/generate",
            params={"plan_id": str(meal_plan_seed.id)}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(x["name"] == "chicken breast" for x in data)

@pytest.mark.asyncio
async def test_get_shopping_list(async_client, grocery_seed):
    resp = await async_client.get("/api/v1/shopping")
    assert resp.status_code == 200
    data = resp.json()

    # Accept list OR grouped structure – we're just asserting it's non-empty
    assert (isinstance(data, list) and len(data) > 0) or (isinstance(data, dict) and data)

    serialized = str(data)
    assert "chicken breast" in serialized

@pytest.mark.asyncio
async def test_toggle_purchased(async_client, grocery_seed):
    resp = await async_client.post(f"/api/v1/shopping/{grocery_seed.id}/toggle")
    assert resp.status_code in (200, 204)

    # If 200 with JSON, assert structure
    if resp.status_code == 200:
        body = resp.json()
        assert "purchased" in body
