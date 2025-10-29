"""
Test Nutrition Profile endpoints (Phase 5.1)
"""
import pytest
from httpx import AsyncClient

from tasteos_api.models.user import User


@pytest.mark.asyncio
@pytest.mark.phase5
async def test_user_can_set_and_get_nutrition_profile(
    async_client: AsyncClient,
    test_user: User,
):
    """
    The user can POST /nutrition/profile to set their profile.
    Then GET /nutrition/profile to see the same data.
    The user_id is always the current user (cannot set another user's profile).
    """

    # 1. Initially, no profile
    resp = await async_client.get("/api/v1/nutrition/profile")
    assert resp.status_code == 404

    # 2. Create/update profile
    create_body = {
        "calories_daily": 2200,
        "protein_daily_g": 140,
        "carbs_daily_g": 220,
        "fat_daily_g": 70,
        "restrictions": {
            "dairy_free": False,
            "shellfish_allergy": False,
        },
        "cultural_notes": "Extra protein for lifting, no dietary restrictions.",
    }
    resp = await async_client.post("/api/v1/nutrition/profile", json=create_body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["calories_daily"] == 2200
    assert data["protein_daily_g"] == 140
    assert data["user_id"] == str(test_user.id)

    # 3. GET profile
    resp = await async_client.get("/api/v1/nutrition/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["calories_daily"] == 2200
    assert data["user_id"] == str(test_user.id)
    assert data["restrictions"]["dairy_free"] is False
