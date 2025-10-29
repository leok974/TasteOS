"""
User nutrition profile models for TasteOS API.

Stores per-user dietary goals, restrictions, and cultural preferences.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class UserNutritionProfileBase(SQLModel):
    """Base schema for user nutrition profiles."""

    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    calories_daily: Optional[int] = None
    protein_daily_g: Optional[int] = None
    carbs_daily_g: Optional[int] = None
    fat_daily_g: Optional[int] = None
    restrictions: dict = Field(default={}, sa_column=Column(JSON))
    cultural_notes: Optional[str] = None


class UserNutritionProfile(UserNutritionProfileBase, BaseModel, table=True):
    """
    User nutrition profile model.

    Stores dietary goals, restrictions, and cultural/religious preferences.
    Examples:
    - calories_daily: 2200
    - protein_daily_g: 140 (high protein for Leo)
    - restrictions: {"dairy_free": true, "shellfish_allergy": true}
    - cultural_notes: "No pork for dad, Halal at home, lighter sodium"

    This is per-user, not per-household, because dietary needs are individual.
    """

    __tablename__ = "user_nutrition_profiles"


class UserNutritionProfileCreate(SQLModel):
    """Schema for creating/updating user nutrition profile (client input)."""

    calories_daily: Optional[int] = None
    protein_daily_g: Optional[int] = None
    carbs_daily_g: Optional[int] = None
    fat_daily_g: Optional[int] = None
    restrictions: Optional[dict] = None
    cultural_notes: Optional[str] = None


class UserNutritionProfileRead(UserNutritionProfileBase):
    """Schema for reading user nutrition profile (API response)."""

    id: UUID
    created_at: datetime
    updated_at: datetime
