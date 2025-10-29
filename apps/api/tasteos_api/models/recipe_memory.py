"""
Recipe Memory model for TasteOS API.

This module defines the RecipeMemory model for storing cultural and household-specific
recipe knowledge (Phase 4 - Family Mode).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Column, Field, SQLModel, JSON

from tasteos_api.models import BaseModel


class RecipeMemoryBase(SQLModel):
    """Base recipe memory schema."""

    household_id: UUID = Field(foreign_key="households.id")
    dish_name: str = Field(max_length=255)
    origin_notes: Optional[str] = None
    substitutions: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    spice_prefs: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    last_cooked_at: Optional[datetime] = None
    created_by_user: UUID = Field(foreign_key="users.id")


class RecipeMemory(RecipeMemoryBase, BaseModel, table=True):
    """Recipe memory database model."""

    __tablename__ = "recipe_memory"


class RecipeMemoryCreate(SQLModel):
    """Schema for recipe memory creation (client input)."""

    dish_name: str = Field(max_length=255)
    origin_notes: Optional[str] = None
    substitutions: Optional[dict] = None
    spice_prefs: Optional[dict] = None
    last_cooked_at: Optional[datetime] = None


class RecipeMemoryRead(RecipeMemoryBase):
    """Schema for recipe memory response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
