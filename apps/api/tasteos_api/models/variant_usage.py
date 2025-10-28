"""
Variant Usage tracking model.

This module defines the database model for tracking daily variant generation
usage per user for quota enforcement.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class VariantUsage(SQLModel, table=True):
    """Track variant generation events for quota enforcement."""

    __tablename__ = "variant_usage"

    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    recipe_id: UUID = Field(foreign_key="recipes.id")
    variant_type: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class VariantUsageRead(SQLModel):
    """Read model for variant usage."""

    id: int
    user_id: UUID
    recipe_id: UUID
    variant_type: str
    created_at: datetime
