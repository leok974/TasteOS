"""
Test the 'money endpoint' /nutrition/today (Phase 5.1)
This evaluates today's meal plan against the household's nutrition goals and restrictions.
"""
import pytest
from httpx import AsyncClient
from tasteos_api.models.user import User
from tasteos_api.models.household import Household
from tasteos_api.models.meal_plan import MealPlan


@pytest.mark.asyncio
@pytest.mark.phase5
async def test_household_nutrition_summary_for_today(
    async_client: AsyncClient,
    test_user: User,
    test_household: Household,
    second_user: User,
    attach_second_user_to_household,
    nutrition_profile_factory,
    todays_household_plan: MealPlan,
):
    """
    Test the complex household nutrition evaluation:
      1. test_user has high protein target, okay with dairy.
      2. second_user is dairy-free.
      3. Today's meal plan includes 'Rasta Pasta (Salmon Cajun)' which has dairy.
      4. /nutrition/today should return per-user assessment with violations and suggestions.
    """

    # 1. Set up profiles for both users
    await nutrition_profile_factory(
        user=test_user,
        calories_daily=2200,
        protein_daily_g=140,
        carbs_daily_g=200,
        fat_daily_g=70,
        restrictions={"dairy_free": False},
        cultural_notes="High protein for lifting",
    )

    await nutrition_profile_factory(
        user=second_user,
        calories_daily=1800,
        protein_daily_g=100,
        carbs_daily_g=180,
        fat_daily_g=60,
        restrictions={"dairy_free": True},
        cultural_notes="No dairy - sensitive stomach",
    )

    # 2. Call /nutrition/today
    resp = await async_client.get("/api/v1/nutrition/today")
    assert resp.status_code == 200
    data = resp.json()

    # 3. Verify response structure
    assert "date" in data
    assert "household_id" in data
    assert "summary" in data
    assert "per_user" in data

    # 4. Check per-user data
    per_user = data["per_user"]
    assert len(per_user) == 2  # test_user and second_user

    # Find second_user in results
    second_user_id_str = str(second_user.id)
    second_user_data = per_user.get(second_user_id_str)
    assert second_user_data is not None

    # 5. Verify dairy violation for second_user
    violations = second_user_data["violations"]
    assert len(violations) > 0
    
    # Should detect dairy in "Rasta Pasta"
    dairy_violation = next((v for v in violations if "dairy" in v["reason"].lower()), None)
    assert dairy_violation is not None
    assert "Rasta Pasta" in dairy_violation["dish"]

    # 6. Verify substitution suggestions
    assert "suggestions" in second_user_data
    assert len(second_user_data["suggestions"]) > 0
    
    # Should suggest coconut milk substitution
    suggestion = second_user_data["suggestions"][0]
    assert "coconut milk" in suggestion.lower() or "substitution" in suggestion.lower()

    # 7. Verify estimated totals (key is 'est_today' in the actual API response)
    estimated = second_user_data["est_today"]
    assert "calories" in estimated
    assert "protein_g" in estimated
    assert estimated["calories"] > 0

    # 8. Verify summary indicates issues
    assert "issue" in data["summary"].lower() or "⚠️" in data["summary"]
