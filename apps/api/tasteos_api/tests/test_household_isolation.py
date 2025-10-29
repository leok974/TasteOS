"""
Phase 4 tests for household isolation and access control.

Tests that pantry, planner, and shopping data is properly scoped by household,
and that users cannot access data from other households.
"""

import pytest

pytestmark = pytest.mark.phase4


@pytest.mark.asyncio
async def test_pantry_household_isolation(async_client, db_session, test_user, test_household):
    """Test that pantry items are isolated by household."""
    from tasteos_api.models.household import Household, HouseholdMembership
    from tasteos_api.models.user import User
    from tasteos_api.models.pantry_item import PantryItem
    import json

    # Create second household with different user
    other_user = User(
        email="other@example.com",
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

    # Add item to other household directly
    other_item = PantryItem(
        user_id=other_user.id,
        household_id=other_household.id,
        added_by_user_id=other_user.id,
        name="secret ingredient",
        quantity=1.0,
        unit="lb",
        tags=json.dumps(["hidden"])
    )
    db_session.add(other_item)
    await db_session.commit()
    await db_session.refresh(other_item)

    # Add item to test household via API
    test_payload = {
        "name": "visible ingredient",
        "quantity": 2.0,
        "unit": "kg",
        "tags": ["public"]
    }
    res = await async_client.post("/api/v1/pantry", json=test_payload)
    assert res.status_code in (200, 201)

    # List pantry - should only see test household's items
    res_list = await async_client.get("/api/v1/pantry")
    assert res_list.status_code == 200
    items = res_list.json()

    # Should see test household item
    assert any(item["name"] == "visible ingredient" for item in items)

    # Should NOT see other household item
    assert not any(item["name"] == "secret ingredient" for item in items)

    # Attempting to delete other household's item should fail
    res_delete = await async_client.delete(f"/api/v1/pantry/{other_item.id}")
    assert res_delete.status_code == 404


@pytest.mark.asyncio
async def test_planner_household_isolation(async_client, db_session, test_user, test_household):
    """Test that meal plans are isolated by household."""
    from tasteos_api.models.household import Household, HouseholdMembership
    from tasteos_api.models.user import User
    from tasteos_api.models.meal_plan import MealPlan
    from datetime import date
    import json

    # Create second household
    other_user = User(
        email="planner@example.com",
        name="Planner User",
        hashed_password="fakehash",
        plan="free",
        subscription_status="active"
    )
    db_session.add(other_user)
    await db_session.flush()

    other_household = Household(name="Planner Household")
    db_session.add(other_household)
    await db_session.flush()

    membership = HouseholdMembership(
        household_id=other_household.id,
        user_id=other_user.id,
        role="owner"
    )
    db_session.add(membership)
    await db_session.commit()

    # Create meal plan for other household
    other_plan = MealPlan(
        user_id=other_user.id,
        household_id=other_household.id,
        date=date.today(),
        breakfast=json.dumps([{"title": "Secret Breakfast"}]),
        lunch=json.dumps([]),
        dinner=json.dumps([]),
        snacks=json.dumps([]),
        notes_per_user=json.dumps({})
    )
    db_session.add(other_plan)
    await db_session.commit()
    await db_session.refresh(other_plan)

    # Attempt to access other household's meal plan
    res_get = await async_client.get(f"/api/v1/planner/{other_plan.id}")
    assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_shopping_household_isolation(async_client, db_session, test_user, test_household, meal_plan_seed):
    """Test that shopping lists are isolated by household."""
    from tasteos_api.models.household import Household, HouseholdMembership
    from tasteos_api.models.user import User
    from tasteos_api.models.grocery_item import GroceryItem

    # Create second household
    other_user = User(
        email="shopper@example.com",
        name="Shopper User",
        hashed_password="fakehash",
        plan="free",
        subscription_status="active"
    )
    db_session.add(other_user)
    await db_session.flush()

    other_household = Household(name="Shopping Household")
    db_session.add(other_household)
    await db_session.flush()

    membership = HouseholdMembership(
        household_id=other_household.id,
        user_id=other_user.id,
        role="owner"
    )
    db_session.add(membership)
    await db_session.commit()

    # Create grocery item for other household
    other_item = GroceryItem(
        user_id=other_user.id,
        household_id=other_household.id,
        name="secret grocery",
        quantity=1.0,
        unit="item",
        purchased=False
    )
    db_session.add(other_item)
    await db_session.commit()
    await db_session.refresh(other_item)

    # List shopping items - should not see other household's items
    res_list = await async_client.get("/api/v1/shopping")
    assert res_list.status_code == 200
    items = res_list.json()

    # Should NOT see other household's item
    assert not any(item["name"] == "secret grocery" for item in items)

    # Attempt to toggle other household's item should fail
    res_toggle = await async_client.post(f"/api/v1/shopping/{other_item.id}/toggle")
    assert res_toggle.status_code == 404


@pytest.mark.asyncio
async def test_multi_user_household_sharing(async_client, db_session, test_household):
    """
    Test that multiple users in the same household can share data.

    This verifies the core Family Mode functionality.
    """
    from tasteos_api.models.household import HouseholdMembership
    from tasteos_api.models.user import User
    from tasteos_api.models.pantry_item import PantryItem
    import json

    # Create second user in SAME household
    second_user = User(
        email="familymember@example.com",
        name="Family Member",
        hashed_password="fakehash",
        plan="free",
        subscription_status="active"
    )
    db_session.add(second_user)
    await db_session.flush()

    # Add second user to test household
    membership = HouseholdMembership(
        household_id=test_household.id,
        user_id=second_user.id,
        role="member"
    )
    db_session.add(membership)
    await db_session.commit()

    # First user adds pantry item via API
    test_payload = {
        "name": "shared milk",
        "quantity": 1.0,
        "unit": "gallon",
        "tags": ["dairy"]
    }
    res = await async_client.post("/api/v1/pantry", json=test_payload)
    assert res.status_code in (200, 201)

    # Second user adds pantry item directly (simulating their API call)
    second_user_item = PantryItem(
        user_id=second_user.id,
        household_id=test_household.id,
        added_by_user_id=second_user.id,
        name="shared eggs",
        quantity=12.0,
        unit="count",
        tags=json.dumps(["protein"])
    )
    db_session.add(second_user_item)
    await db_session.commit()

    # List pantry via API (as first user via test_user fixture)
    # Should see items from BOTH users because they're in same household
    res_list = await async_client.get("/api/v1/pantry")
    assert res_list.status_code == 200
    items = res_list.json()

    # Should see both users' items
    assert any(item["name"] == "shared milk" for item in items)
    assert any(item["name"] == "shared eggs" for item in items)
    assert len(items) >= 2
