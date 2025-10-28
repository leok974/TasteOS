"""
Recipe model for TasteOS API.

This module defines the Recipe SQLModel class and related schemas
for recipe management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, JSON, Column

from tasteos_api.models import BaseModel


class RecipeBase(SQLModel):
    """Base recipe schema with common fields."""

    title: str
    description: str
    servings: int = 4
    prep_time: int  # minutes
    cook_time: int  # minutes
    difficulty: str = "medium"  # easy, medium, hard
    cuisine: str = "general"
    is_public: bool = False


class Recipe(RecipeBase, BaseModel, table=True):
    """Recipe database model."""

    __tablename__ = "recipes"

    total_time: int  # computed: prep_time + cook_time
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)

    # JSON fields for complex data
    tags: str = Field(default="[]", sa_column=Column(JSON))  # List of tags
    ingredients: str = Field(default="[]", sa_column=Column(JSON))  # List of ingredients
    instructions: str = Field(default="[]", sa_column=Column(JSON))  # List of instructions
    nutrition: Optional[str] = Field(default=None, sa_column=Column(JSON))  # Nutrition info
    images: str = Field(default="[]", sa_column=Column(JSON))  # List of image URLs
    source: Optional[str] = Field(default=None, sa_column=Column(JSON))  # Recipe source info

    rating: Optional[float] = None


class RecipeCreate(RecipeBase):
    """Schema for recipe creation."""

    tags: list[str] = []
    ingredients: list[dict] = []
    instructions: list[dict] = []
    nutrition: Optional[dict] = None
    images: list[str] = []
    source: Optional[dict] = None


class RecipeUpdate(SQLModel):
    """Schema for recipe updates."""

    title: Optional[str] = None
    description: Optional[str] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    difficulty: Optional[str] = None
    cuisine: Optional[str] = None
    tags: Optional[list[str]] = None
    ingredients: Optional[list[dict]] = None
    instructions: Optional[list[dict]] = None
    is_public: Optional[bool] = None


class RecipeRead(RecipeBase):
    """Schema for recipe response."""

    id: UUID
    user_id: Optional[UUID]
    total_time: int
    tags: list[str]
    ingredients: list[dict]
    instructions: list[dict]
    nutrition: Optional[dict]
    images: list[str]
    source: Optional[dict]
    rating: Optional[float]
    created_at: datetime
    updated_at: datetime
