"""
Core models for TasteOS API.

This module contains the base SQLModel classes and shared database models.
"""

# pyright: reportUnusedImport=false
# These imports are intentionally re-exported so Alembic / SQLModel sees all models.
# mypy: disable-error-code="misc"
# Pylance: ignore SQLModel Field() generic inference noise

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class BaseModel(SQLModel):
    """Base model with common fields for all entities."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TimestampMixin(SQLModel):
    """Mixin for models that need timestamp tracking."""

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# Import all models for Alembic to discover
from tasteos_api.models.user import User  # noqa: E402, F401
from tasteos_api.models.recipe import Recipe  # noqa: E402, F401
from tasteos_api.models.variant import RecipeVariant  # noqa: E402, F401
from tasteos_api.models.billing_event import BillingEvent  # noqa: E402, F401
from tasteos_api.models.recipe_nutrition import RecipeNutrition  # noqa: E402, F401
from tasteos_api.models.pantry_item import PantryItem  # noqa: E402, F401
from tasteos_api.models.meal_plan import MealPlan  # noqa: E402, F401
from tasteos_api.models.grocery_item import GroceryItem  # noqa: E402, F401
from tasteos_api.models.household import Household, HouseholdMembership  # noqa: E402, F401
from tasteos_api.models.recipe_memory import RecipeMemory  # noqa: E402, F401
from tasteos_api.models.user_nutrition_profile import UserNutritionProfile  # noqa: E402, F401
from tasteos_api.models.recipe_nutrition_info import RecipeNutritionInfo  # noqa: E402, F401

