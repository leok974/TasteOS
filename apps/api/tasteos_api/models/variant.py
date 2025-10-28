"""
Variant model for TasteOS API.

This module defines the RecipeVariant SQLModel class and related schemas
for AI-generated recipe variants.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, JSON, Column

from tasteos_api.models import BaseModel


class VariantBase(SQLModel):
    """Base variant schema with common fields."""

    title: str
    description: str
    variant_type: str  # dietary, cuisine, technique, ingredient, etc.
    status: str = "draft"  # draft, generated, reviewed, tested, approved


class RecipeVariant(VariantBase, BaseModel, table=True):
    """Recipe variant database model."""

    __tablename__ = "recipe_variants"

    parent_recipe_id: UUID = Field(foreign_key="recipes.id", index=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)

    # JSON fields for complex data
    changes: str = Field(default="[]", sa_column=Column(JSON))  # List of changes
    generation_metadata: str = Field(default="{}", sa_column=Column(JSON))  # Variant metadata

    confidence_score: float = 0.0  # AI confidence 0-1


class VariantCreate(VariantBase):
    """Schema for variant creation."""

    parent_recipe_id: UUID
    changes: list[dict] = []
    generation_metadata: dict = {}


class VariantUpdate(SQLModel):
    """Schema for variant updates."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    changes: Optional[list[dict]] = None
    generation_metadata: Optional[dict] = None


class VariantRead(VariantBase):
    """Schema for variant response."""

    id: UUID
    parent_recipe_id: UUID
    user_id: Optional[UUID]
    changes: list[dict]
    generation_metadata: dict
    confidence_score: float
    created_at: datetime
    updated_at: datetime
