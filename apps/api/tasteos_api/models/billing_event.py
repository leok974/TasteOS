"""
Billing event model for TasteOS API.

This model tracks Stripe webhook events for audit and debugging purposes.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, Column, JSON

from tasteos_api.models import BaseModel


class BillingEvent(BaseModel, table=True):
    """
    Track billing events from Stripe webhooks.

    This table logs all incoming webhook events for audit purposes
    and helps debug subscription/payment issues.
    """

    __tablename__ = "billing_events"

    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)

    # Stripe event details
    event_type: str = Field(index=True)  # e.g., "checkout.session.completed"
    stripe_event_id: str = Field(unique=True, index=True)  # e.g., "evt_xxx"
    stripe_customer_id: Optional[str] = Field(default=None, index=True)

    # Event payload (stored as JSON for reference)
    event_data: str = Field(sa_column=Column(JSON))

    # Processing status
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
