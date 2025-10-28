"""
Usage tracking model for billing.

This module tracks user usage for billing and quota enforcement.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, JSON, Column

from tasteos_api.models import BaseModel


class UsageBase(SQLModel):
    """Base usage schema with common fields."""

    period: str  # YYYY-MM format
    variants_generated: int = 0
    recipes_imported: int = 0
    cooking_sessions: int = 0


class Usage(UsageBase, BaseModel, table=True):
    """Usage tracking database model."""

    __tablename__ = "usage"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    features: str = Field(default="{}", sa_column=Column(JSON))  # Additional feature usage


class UsageRead(UsageBase):
    """Schema for usage response."""

    id: UUID
    user_id: UUID
    features: dict
    created_at: datetime
    updated_at: datetime


class UsageUpdate(SQLModel):
    """Schema for usage updates."""

    variants_generated: Optional[int] = None
    recipes_imported: Optional[int] = None
    cooking_sessions: Optional[int] = None
    features: Optional[dict] = None
