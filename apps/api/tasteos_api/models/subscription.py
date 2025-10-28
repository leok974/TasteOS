"""
Subscription model for billing.

This module handles user subscription data for Stripe integration.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from tasteos_api.models import BaseModel


class SubscriptionBase(SQLModel):
    """Base subscription schema with common fields."""

    plan: str  # free, pro, enterprise
    status: str  # active, canceled, past_due, unpaid, trialing
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False


class Subscription(SubscriptionBase, BaseModel, table=True):
    """Subscription database model."""

    __tablename__ = "subscriptions"

    user_id: UUID = Field(foreign_key="users.id", index=True, unique=True)
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None


class SubscriptionRead(SubscriptionBase):
    """Schema for subscription response."""

    id: UUID
    user_id: UUID
    stripe_subscription_id: Optional[str]
    stripe_customer_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class SubscriptionUpdate(SQLModel):
    """Schema for subscription updates."""

    plan: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
