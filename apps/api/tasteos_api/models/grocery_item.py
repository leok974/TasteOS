"""
Grocery item model for TasteOS API.

This model represents items in a shopping list derived from meal plans.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class GroceryItem(BaseModel, table=True):
    """
    Represents an item in a shopping list.

    Shopping lists are generated from meal plans by comparing required
    ingredients against what's already in the user's pantry.
    """

    __tablename__ = "grocery_items"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    household_id: UUID = Field(foreign_key="households.id", index=True)
    meal_plan_id: Optional[UUID] = Field(default=None, foreign_key="meal_plans.id", index=True)
    assigned_to_user: Optional[UUID] = Field(default=None, foreign_key="users.id")

    # Item details
    name: str = Field(index=True)
    quantity: Optional[float] = None
    unit: Optional[str] = None

    # Purchase tracking
    purchased: bool = Field(default=False)


class GroceryItemCreate(SQLModel):
    """Schema for creating a grocery item."""

    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    meal_plan_id: Optional[UUID] = None


class GroceryItemRead(SQLModel):
    """Schema for reading a grocery item."""

    id: UUID
    user_id: UUID
    meal_plan_id: Optional[UUID]
    name: str
    quantity: Optional[float]
    unit: Optional[str]
    purchased: bool
    created_at: datetime
    updated_at: datetime


class GroceryItemUpdate(SQLModel):
    """Schema for updating a grocery item."""

    purchased: Optional[bool] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
