"""
Pantry item model for TasteOS API.

This model tracks ingredients and items in a user's pantry.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlmodel import Field, Column, JSON, SQLModel

from tasteos_api.models import BaseModel


class PantryItem(BaseModel, table=True):
    """
    Represents an item in a user's pantry.

    Tracks what ingredients the user has on hand, including
    quantities, units, expiration dates, and categorization tags.
    """

    __tablename__ = "pantry_items"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    household_id: UUID = Field(foreign_key="households.id", index=True)
    added_by_user_id: UUID = Field(foreign_key="users.id")

    # Item details
    name: str = Field(index=True)  # e.g., "chicken breast", "onion"
    quantity: Optional[float] = None  # e.g., 2.5
    unit: Optional[str] = None  # e.g., "lb", "g", "ml", "pcs", "cups"

    # Freshness tracking
    expires_at: Optional[datetime] = None

    # Categorization
    tags: str = Field(default="[]", sa_column=Column(JSON))  # Store as JSON array


class PantryItemCreate(SQLModel):
    """Schema for creating a pantry item."""

    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expires_at: Optional[datetime] = None
    tags: List[str] = []


class PantryItemRead(SQLModel):
    """Schema for reading a pantry item."""

    id: UUID
    user_id: UUID
    name: str
    quantity: Optional[float]
    unit: Optional[str]
    expires_at: Optional[datetime]
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class PantryItemUpdate(SQLModel):
    """Schema for updating a pantry item."""

    quantity: Optional[float] = None
    unit: Optional[str] = None
    expires_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
