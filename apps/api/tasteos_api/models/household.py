"""
Household models for TasteOS API.

This module defines household and membership models for family sharing (Phase 4).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from tasteos_api.models import BaseModel


class HouseholdBase(SQLModel):
    """Base household schema."""

    name: str = Field(max_length=255)


class Household(HouseholdBase, BaseModel, table=True):
    """Household database model."""

    __tablename__ = "households"

    # Relationships will be added as needed
    # members: list["HouseholdMembership"] = Relationship(back_populates="household")


class HouseholdCreate(HouseholdBase):
    """Schema for household creation."""

    pass


class HouseholdRead(HouseholdBase):
    """Schema for household response."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class HouseholdMembershipBase(SQLModel):
    """Base household membership schema."""

    household_id: UUID = Field(foreign_key="households.id")
    user_id: UUID = Field(foreign_key="users.id")
    role: str = Field(default="member")  # owner, member


class HouseholdMembership(HouseholdMembershipBase, BaseModel, table=True):
    """Household membership database model."""

    __tablename__ = "household_memberships"

    joined_at: datetime = Field(default_factory=lambda: datetime.now())

    # Relationships
    # household: Optional[Household] = Relationship(back_populates="members")
    # user: Optional["User"] = Relationship()


class HouseholdMembershipCreate(HouseholdMembershipBase):
    """Schema for membership creation."""

    pass


class HouseholdMembershipRead(HouseholdMembershipBase):
    """Schema for membership response."""

    id: UUID
    joined_at: datetime
    created_at: datetime
    updated_at: datetime
