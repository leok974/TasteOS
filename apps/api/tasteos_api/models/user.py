"""
User model for TasteOS API.

This module defines the User SQLModel class and related schemas
for user authentication and profile management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class UserBase(SQLModel):
    """Base user schema with common fields."""

    email: str = Field(unique=True, index=True)
    name: str
    is_active: bool = True
    plan: str = "free"  # free, pro_monthly, pro_yearly, enterprise
    subscription_status: str = "active"  # active, past_due, canceled, trialing


class User(UserBase, BaseModel, table=True):
    """User database model."""

    __tablename__ = "users"

    hashed_password: str
    avatar: Optional[str] = None
    preferences: Optional[str] = None  # JSON string
    last_login: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None  # Stripe customer ID for billing


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str


class UserUpdate(SQLModel):
    """Schema for user updates."""

    name: Optional[str] = None
    avatar: Optional[str] = None
    preferences: Optional[str] = None


class UserRead(UserBase):
    """Schema for user response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
