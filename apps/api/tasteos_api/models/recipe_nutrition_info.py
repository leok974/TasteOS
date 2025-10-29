"""
Recipe nutrition info models for TasteOS API.

Stores computed nutrition data for household recipe memories.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class RecipeNutritionInfoBase(SQLModel):
    """Base schema for recipe nutrition info."""

    recipe_memory_id: UUID = Field(foreign_key="recipe_memory.id", unique=True, index=True)
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    micronotes: dict = Field(default={}, sa_column=Column(JSON))
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeNutritionInfo(RecipeNutritionInfoBase, BaseModel, table=True):
    """
    Recipe nutrition info model.

    Stores computed nutrition data for a household's recipe memory.
    This is culturally-aware nutrition: "YOUR family's Rasta Pasta"
    not generic "internet recipe calories."

    Example:
    - recipe_memory_id: FK to "Rasta Pasta (Salmon Cajun)"
    - calories: 650
    - protein_g: 32.0
    - carbs_g: 48.0
    - fat_g: 28.0
    - micronotes: {"sodium_mg": 800, "fiber_g": 6, "vitamin_c_mg": 45}
    - computed_at: when nutrition was calculated

    Can be mocked initially, later wired to Edamam/OpenFoodFacts/nutrition API.
    """

    __tablename__ = "recipe_nutrition_info"


class RecipeNutritionInfoCreate(SQLModel):
    """Schema for creating recipe nutrition info (client input)."""

    recipe_memory_id: UUID
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    micronotes: Optional[dict] = None


class RecipeNutritionInfoRead(RecipeNutritionInfoBase):
    """Schema for reading recipe nutrition info (API response)."""

    id: UUID
    created_at: datetime
    updated_at: datetime
