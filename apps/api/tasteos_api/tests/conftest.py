import json
from datetime import datetime, timedelta, date, timezone
from types import SimpleNamespace
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from tasteos_api.main import app
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.household import Household, HouseholdMembership
from tasteos_api.models.pantry_item import PantryItem
from tasteos_api.models.meal_plan import MealPlan
from tasteos_api.models.grocery_item import GroceryItem

# ------------------------------------------------------------------
# 1. Async test engine + sessionmaker
# ------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

AsyncTestingSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ------------------------------------------------------------------
# 2. Create/drop schema once per test session
# ------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with async_engine.begin() as conn:
        # Create all tables for tests
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # (We could drop after if we want, but in-memory sqlite will vanish anyway)


# ------------------------------------------------------------------
# 3. Per-test DB session fixture
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncTestingSessionLocal() as session:
        yield session
        # Rollback any leftover state to keep tests isolated
        await session.rollback()


# ------------------------------------------------------------------
# 4. Fake current user + override dependencies
# ------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    from sqlmodel import select
    # Try to find existing user first
    result = await db_session.exec(select(User).where(User.email == "testuser@example.com"))
    user = result.first()

    if user is None:
        user = User(
            email="testuser@example.com",
            name="Test User",
            hashed_password="fakehash",
            plan="free",
            subscription_status="active",
            stripe_customer_id=None,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    return user


@pytest_asyncio.fixture(scope="function")
async def test_household(db_session: AsyncSession, test_user: User) -> Household:
    """
    Create a test household and link the test user to it.
    Phase 4: Every test user belongs to a household.
    """
    from sqlmodel import select

    # Check if household already exists
    result = await db_session.exec(
        select(Household).where(Household.name == "Test Household")
    )
    household = result.first()

    if household is None:
        household = Household(name="Test Household")
        db_session.add(household)
        await db_session.flush()

        # Create membership
        membership = HouseholdMembership(
            household_id=household.id,
            user_id=test_user.id,
            role="owner"
        )
        db_session.add(membership)
        await db_session.commit()
        await db_session.refresh(household)

    return household


def override_get_db_session(db_session: AsyncSession):
    async def _override():
        # FastAPI Depends expects a callable that yields the session
        yield db_session
    return _override


def override_get_current_user(user: User):
    async def _override():
        return user
    return _override


def override_get_current_household(household: Household):
    """
    Override get_current_household for tests.
    Returns a SimpleNamespace with id and name matching the test household.
    """
    async def _override():
        return SimpleNamespace(id=household.id, name=household.name)
    return _override


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession, test_user: User, test_household: Household):
    # Override DB dep
    app.dependency_overrides[get_db_session] = override_get_db_session(db_session)

    # Override auth dep
    # Imports inline to avoid circular import at module import time
    from tasteos_api.core.dependencies import get_current_user as real_user_dep
    app.dependency_overrides[real_user_dep] = override_get_current_user(test_user)

    # Override household dep (Phase 4)
    from tasteos_api.core.dependencies import get_current_household as real_household_dep
    app.dependency_overrides[real_household_dep] = override_get_current_household(test_household)

    # Use ASGITransport for httpx AsyncClient with follow_redirects
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=True
    ) as client:
        yield client

    # Clean up overrides after test
    app.dependency_overrides.clear()


# ------------------------------------------------------------------
# 5. Seed fixtures
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def pantry_seed(db_session: AsyncSession, test_user: User, test_household: Household):
    item = PantryItem(
        user_id=test_user.id,
        household_id=test_household.id,
        added_by_user_id=test_user.id,
        name="chicken breast",
        quantity=2.0,
        unit="lb",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        # tags is a JSON/text field in your model, so serialize here:
        tags=json.dumps(["protein", "lean"]),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def meal_plan_seed(db_session: AsyncSession, test_user: User, test_household: Household):
    from sqlmodel import select
    # Check if plan already exists for today
    result = await db_session.exec(
        select(MealPlan).where(
            MealPlan.user_id == test_user.id,
            MealPlan.household_id == test_household.id,
            MealPlan.date == date.today()
        )
    )
    day_plan = result.first()

    if day_plan is None:
        day_plan = MealPlan(
            user_id=test_user.id,
            household_id=test_household.id,
            date=date.today(),
            breakfast=json.dumps([{"recipe_id": "r1", "title": "Egg Whites Scramble"}]),
            lunch=json.dumps([{"recipe_id": "r2", "title": "Grilled Chicken Bowl"}]),
            dinner=json.dumps([{"recipe_id": "r3", "title": "Salmon + Greens"}]),
            snacks=json.dumps([{"recipe_id": "r4", "title": "Greek Yogurt"}]),
            notes_per_user=json.dumps({}),
            total_calories=2100,
            notes="High protein day 💪",
        )
        db_session.add(day_plan)
        await db_session.commit()
        await db_session.refresh(day_plan)

    return day_plan


@pytest_asyncio.fixture
async def grocery_seed(db_session: AsyncSession, test_user: User, test_household: Household, meal_plan_seed: MealPlan):
    g = GroceryItem(
        user_id=test_user.id,
        household_id=test_household.id,
        meal_plan_id=meal_plan_seed.id,
        name="chicken breast",
        quantity=2.0,
        unit="lb",
        purchased=False,
        assigned_to_user=None,
    )
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g


# ------------------------------------------------------------------
# 6. Phase 5.1 fixtures (nutrition profiles & multi-user)
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    """
    Create a second user in the system so we can simulate multiple household members.
    """
    u = User(
        email="second_user+tasteos@example.com",
        name="Second User",
        hashed_password="hashed_password_placeholder",  # Required field
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def attach_second_user_to_household(
    db_session: AsyncSession,
    test_household: Household,
    second_user: User,
):
    """
    Add second_user to the same household as test_user with role='member'.
    """
    membership = HouseholdMembership(
        household_id=test_household.id,
        user_id=second_user.id,
        role="member",
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership


@pytest_asyncio.fixture
async def nutrition_profile_factory(db_session: AsyncSession):
    """
    Factory fixture to create or update a UserNutritionProfile.
    Usage in tests:
        await nutrition_profile_factory(user=test_user, calories_daily=2200, ...)
    """

    async def _create_profile(
        user: User,
        calories_daily: int = None,
        protein_daily_g: int = None,
        carbs_daily_g: int = None,
        fat_daily_g: int = None,
        restrictions: dict = None,
        cultural_notes: str = None,
    ):
        from tasteos_api.models.user_nutrition_profile import UserNutritionProfile
        from sqlmodel import select
        
        # Try existing profile (unique per user)
        q = select(UserNutritionProfile).where(UserNutritionProfile.user_id == user.id)
        res = await db_session.exec(q)
        profile = res.first()

        if profile is None:
            profile = UserNutritionProfile(user_id=user.id)

        profile.calories_daily = calories_daily
        profile.protein_daily_g = protein_daily_g
        profile.carbs_daily_g = carbs_daily_g
        profile.fat_daily_g = fat_daily_g
        profile.restrictions = restrictions or {}
        profile.cultural_notes = cultural_notes or ""

        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        return profile

    return _create_profile


@pytest_asyncio.fixture
async def recipe_with_nutrition_factory(db_session: AsyncSession, test_household: Household, test_user: User):
    """
    Factory to create a RecipeMemory + RecipeNutritionInfo pair representing a culturally-scoped dish.
    Returns SimpleNamespace(memory=..., nutrition=...)
    """
    from tasteos_api.models.recipe_memory import RecipeMemory
    from tasteos_api.models.recipe_nutrition_info import RecipeNutritionInfo
    from types import SimpleNamespace

    async def _create_recipe(
        dish_name: str,
        calories: int = None,
        protein_g: float = None,
        carbs_g: float = None,
        fat_g: float = None,
        micronotes: dict = None,
        origin_notes: str = "Family version",
    ):
        memory = RecipeMemory(
            household_id=test_household.id,
            dish_name=dish_name,
            origin_notes=origin_notes,
            substitutions={"note": "coconut milk instead of cream"},
            spice_prefs={"Mom": "mild", "Leo": "medium-high"},
            created_by_user=test_user.id,
        )
        db_session.add(memory)
        await db_session.flush()

        nutrition = RecipeNutritionInfo(
            recipe_memory_id=memory.id,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            micronotes=micronotes or {},
        )
        db_session.add(nutrition)

        await db_session.commit()
        await db_session.refresh(memory)
        await db_session.refresh(nutrition)

        return SimpleNamespace(memory=memory, nutrition=nutrition)

    return _create_recipe


@pytest_asyncio.fixture
async def todays_household_plan(
    db_session: AsyncSession,
    test_household: Household,
    test_user: User,
    recipe_with_nutrition_factory,
):
    """
    Create a MealPlan for today for this household.
    We'll attach dishes to breakfast/lunch/dinner in a way that we expect /nutrition/today to inspect.
    """

    # Create two known dishes with nutrition info
    r1 = await recipe_with_nutrition_factory(
        dish_name="Rasta Pasta (Salmon Cajun)",
        calories=650,
        protein_g=32.0,
        carbs_g=48.0,
        fat_g=28.0,
        micronotes={"dairy": True},
        origin_notes="Sunday routine sauce: coconut milk + heavy cream",
    )

    r2 = await recipe_with_nutrition_factory(
        dish_name="Grilled Chicken Bowl",
        calories=500,
        protein_g=40.0,
        carbs_g=30.0,
        fat_g=18.0,
        micronotes={"dairy": False},
        origin_notes="High protein go-to",
    )

    # MealPlan breakfast/lunch/dinner/snacks are JSON arrays of dish names
    plan = MealPlan(
        household_id=test_household.id,
        user_id=test_user.id,
        date=date.today(),
        breakfast=[r2.memory.dish_name],  # Grilled Chicken Bowl
        lunch=[r2.memory.dish_name],      # Grilled Chicken Bowl
        dinner=[r1.memory.dish_name],     # Rasta Pasta (has dairy)
        snacks=[],
        notes_per_user={},
        total_calories=1650,
        notes="High protein plan with dairy warning",
    )

    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    return plan
