import asyncio
import json
from datetime import datetime, timedelta, date
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from tasteos_api.main import app
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
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
    result = await db_session.execute(select(User).where(User.email == "testuser@example.com"))
    user = result.scalar_one_or_none()

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


def override_get_db_session(db_session: AsyncSession):
    async def _override():
        # FastAPI Depends expects a callable that yields the session
        yield db_session
    return _override


def override_get_current_user(user: User):
    async def _override():
        return user
    return _override


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession, test_user: User):
    # Override DB dep
    app.dependency_overrides[get_db_session] = override_get_db_session(db_session)

    # Override auth dep
    # Imports inline to avoid circular import at module import time
    from tasteos_api.core.dependencies import get_current_user as real_dep
    app.dependency_overrides[real_dep] = override_get_current_user(test_user)

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
async def pantry_seed(db_session: AsyncSession, test_user: User):
    item = PantryItem(
        user_id=test_user.id,
        name="chicken breast",
        quantity=2.0,
        unit="lb",
        expires_at=datetime.utcnow() + timedelta(days=2),
        # tags is a JSON/text field in your model, so serialize here:
        tags=json.dumps(["protein", "lean"]),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def meal_plan_seed(db_session: AsyncSession, test_user: User):
    from sqlmodel import select
    # Check if plan already exists for today
    result = await db_session.execute(
        select(MealPlan).where(
            MealPlan.user_id == test_user.id,
            MealPlan.date == date.today()
        )
    )
    day_plan = result.first()
    if day_plan:
        day_plan = day_plan[0]  # Extract from tuple

    if day_plan is None:
        day_plan = MealPlan(
            user_id=test_user.id,
            date=date.today(),
            breakfast=json.dumps([{"recipe_id": "r1", "title": "Egg Whites Scramble"}]),
            lunch=json.dumps([{"recipe_id": "r2", "title": "Grilled Chicken Bowl"}]),
            dinner=json.dumps([{"recipe_id": "r3", "title": "Salmon + Greens"}]),
            snacks=json.dumps([{"recipe_id": "r4", "title": "Greek Yogurt"}]),
            total_calories=2100,
            notes="High protein day 💪",
        )
        db_session.add(day_plan)
        await db_session.commit()
        await db_session.refresh(day_plan)

    return day_plan


@pytest_asyncio.fixture
async def grocery_seed(db_session: AsyncSession, test_user: User, meal_plan_seed: MealPlan):
    g = GroceryItem(
        user_id=test_user.id,
        meal_plan_id=meal_plan_seed.id,
        name="chicken breast",
        quantity=2.0,
        unit="lb",
        purchased=False,
    )
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g
