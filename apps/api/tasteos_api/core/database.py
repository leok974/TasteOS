"""
Database configuration and connection management.

This module handles database connection setup, session management,
and initialization for the TasteOS API using SQLModel.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from tasteos_api.core.config import get_settings

settings = get_settings()

# Create database engine
if settings.database_url.startswith("sqlite"):
    # SQLite configuration
    engine = create_async_engine(
        settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=settings.environment == "development",
        future=True,
    )
else:
    # PostgreSQL configuration
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.environment == "development",
        future=True,
        pool_pre_ping=True,
        pool_recycle=300,
    )


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from tasteos_api.models import (  # noqa: F401
            recipe,
            subscription,
            usage,
            user,
            variant,
            variant_usage,
            pantry_item,
            meal_plan,
            grocery_item,
            household,
            household_invite,
            user_nutrition_profile,
            recipe_nutrition_info,
        )

        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with SQLModelAsyncSession(engine) as session:
        try:
            yield session
        finally:
            await session.close()
