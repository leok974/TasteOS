"""
Phase 4 tests for Recipe Memory router.

Tests household-scoped recipe memory storage for cultural knowledge,
substitutions, and cooking preferences.
"""

from datetime import datetime, timezone
import pytest

pytestmark = pytest.mark.phase4


@pytest.mark.asyncio
async def test_create_and_list_memory(async_client, db_session, test_user, test_household):
    """Test creating and listing recipe memories for a household."""
    create_payload = {
        "dish_name": "Rasta Pasta (Salmon Cajun)",
        "origin_notes": "Sunday routine, coconut milk + heavy cream.",
        "substitutions": {
            "protein": "salmon, skin off",
            "sauce": "coconut milk + heavy cream",
            "seasoning": "Cajun on salmon only"
        },
        "spice_prefs": {
            "Leo": "medium-high Cajun heat",
            "Mom": "mild, no extra pepper flakes"
        },
        "last_cooked_at": None
    }

    # Create memory
    res_create = await async_client.post("/api/v1/memory", json=create_payload)
    assert res_create.status_code in (200, 201)
    body = res_create.json()
    assert body["dish_name"] == "Rasta Pasta (Salmon Cajun)"
    assert body["origin_notes"] == "Sunday routine, coconut milk + heavy cream."
    assert body["household_id"] == str(test_household.id)
    assert body["created_by_user"] == str(test_user.id)
    memory_id = body["id"]

    # List memories
    res_list = await async_client.get("/api/v1/memory")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data) >= 1
    assert any(item["dish_name"] == "Rasta Pasta (Salmon Cajun)" for item in data)


@pytest.mark.asyncio
async def test_get_memory_by_id(async_client, db_session, test_user, test_household):
    """Test retrieving a specific recipe memory by ID."""
    create_payload = {
        "dish_name": "Sunday Roast Chicken",
        "origin_notes": "Grandma's recipe from Jamaica",
        "substitutions": {"herbs": "thyme + scallions"},
        "spice_prefs": {"family": "jerk seasoning blend"},
        "last_cooked_at": None
    }

    # Create
    res_create = await async_client.post("/api/v1/memory", json=create_payload)
    assert res_create.status_code in (200, 201)
    memory_id = res_create.json()["id"]

    # Get by ID
    res_get = await async_client.get(f"/api/v1/memory/{memory_id}")
    assert res_get.status_code == 200
    body = res_get.json()
    assert body["id"] == memory_id
    assert body["dish_name"] == "Sunday Roast Chicken"
    assert body["origin_notes"] == "Grandma's recipe from Jamaica"


@pytest.mark.asyncio
async def test_delete_memory(async_client, db_session, test_user, test_household):
    """Test deleting a recipe memory."""
    create_payload = {
        "dish_name": "Test Dish",
        "origin_notes": "Test notes",
        "substitutions": {},
        "spice_prefs": {},
        "last_cooked_at": None
    }

    # Create
    res_create = await async_client.post("/api/v1/memory", json=create_payload)
    assert res_create.status_code in (200, 201)
    memory_id = res_create.json()["id"]

    # Delete
    res_delete = await async_client.delete(f"/api/v1/memory/{memory_id}")
    assert res_delete.status_code == 204

    # Verify deleted
    res_get = await async_client.get(f"/api/v1/memory/{memory_id}")
    assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_memory_household_isolation(async_client, db_session, test_user, test_household):
    """
    Test that recipe memories are isolated by household.

    Users in different households should not see each other's memories.
    """
    from tasteos_api.models.household import Household, HouseholdMembership
    from tasteos_api.models.user import User
    from sqlmodel import select

    # Create a second household with a different user
    other_user = User(
        email="otheruser@example.com",
        name="Other User",
        hashed_password="fakehash",
        plan="free",
        subscription_status="active"
    )
    db_session.add(other_user)
    await db_session.flush()

    other_household = Household(name="Other Household")
    db_session.add(other_household)
    await db_session.flush()

    membership = HouseholdMembership(
        household_id=other_household.id,
        user_id=other_user.id,
        role="owner"
    )
    db_session.add(membership)
    await db_session.commit()

    # Create memory in test household (via API with test_household override)
    payload_test = {
        "dish_name": "Test Household Dish",
        "origin_notes": "Only visible to test household",
        "substitutions": {},
        "spice_prefs": {},
        "last_cooked_at": None
    }
    res = await async_client.post("/api/v1/memory", json=payload_test)
    assert res.status_code in (200, 201)
    test_memory_id = res.json()["id"]

    # Create memory directly in other household (bypass API)
    from tasteos_api.models.recipe_memory import RecipeMemory
    other_memory = RecipeMemory(
        household_id=other_household.id,
        dish_name="Other Household Dish",
        origin_notes="Only visible to other household",
        created_by_user=other_user.id,
        substitutions={},
        spice_prefs={}
    )
    db_session.add(other_memory)
    await db_session.commit()
    await db_session.refresh(other_memory)

    # List memories via API (should only see test household's memory)
    res_list = await async_client.get("/api/v1/memory")
    assert res_list.status_code == 200
    memories = res_list.json()

    # Should see test household memory
    assert any(m["dish_name"] == "Test Household Dish" for m in memories)

    # Should NOT see other household memory
    assert not any(m["dish_name"] == "Other Household Dish" for m in memories)

    # Attempting to access other household's memory should return 404
    res_get_other = await async_client.get(f"/api/v1/memory/{other_memory.id}")
    assert res_get_other.status_code == 404
