"""
Household invite models for TasteOS API.

Enables household owners to invite new members via secure token.
"""

import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class HouseholdInviteBase(SQLModel):
    """Base schema for household invites."""

    household_id: UUID = Field(foreign_key="households.id", index=True)
    invited_email: str = Field(max_length=255, index=True)
    role: str = Field(default="member", max_length=50)  # "owner" or "member"
    token: str = Field(unique=True, index=True, max_length=255)
    revoked: bool = Field(default=False)
    accepted_at: Optional[datetime] = None


class HouseholdInvite(HouseholdInviteBase, BaseModel, table=True):
    """
    Household invite table model.
    
    Represents an invitation to join a household. Owner creates invite with token,
    invitee redeems token to join household.
    """

    __tablename__ = "household_invites"

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for invitation."""
        return secrets.token_urlsafe(16)


class HouseholdInviteCreate(SQLModel):
    """Schema for creating a household invite."""

    invited_email: str
    role: str = "member"


class HouseholdInviteRead(HouseholdInviteBase):
    """Schema for reading a household invite."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class HouseholdInviteToken(SQLModel):
    """Schema for returning just the invite token."""

    token: str
    household_id: UUID
