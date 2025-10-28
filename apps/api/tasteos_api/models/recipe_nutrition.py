"""
Recipe nutrition model for TasteOS API.

This model stores calculated nutritional information for recipes and variants.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class RecipeNutrition(BaseModel, table=True):
    """
    Nutritional information for recipes and variants.

    This table caches nutrition calculations so we don't have to
    recalculate every time. Each recipe or variant has one row
    with its most recent nutrition data.
    """

    __tablename__ = "recipe_nutrition"

    recipe_id: UUID = Field(foreign_key="recipes.id", index=True)
    variant_id: Optional[UUID] = Field(default=None, foreign_key="recipe_variants.id", index=True)

    # Macros per serving
    calories: int  # kcal per serving
    protein_g: float  # grams of protein per serving
    carbs_g: float  # grams of carbohydrates per serving
    fat_g: float  # grams of fat per serving

    # Optional notes about the nutrition profile
    notes: Optional[str] = None

    # Track when this was calculated
    # (inherits created_at and updated_at from BaseModel)


class RecipeNutritionRead(SQLModel):
    """Schema for nutrition response."""

    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    notes: Optional[str] = None
