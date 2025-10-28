"""
Billing router for subscription management.

This module provides endpoints for handling Stripe subscriptions,
webhooks, and billing operations.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.config import get_settings
from tasteos_api.core.database import get_db_session
from tasteos_api.core.dependencies import get_current_user
from tasteos_api.core.quotas import get_daily_variant_usage, DAILY_VARIANT_QUOTAS
from tasteos_api.models.subscription import Subscription, SubscriptionRead
from tasteos_api.models.usage import Usage, UsageRead
from tasteos_api.models.user import User
from tasteos_api.models.billing_event import BillingEvent

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

router = APIRouter()

# Plan limits
PLAN_LIMITS = {
    "free": {
        "variants_per_month": 10,
        "recipes_imported_per_month": 5,
        "cooking_sessions_per_month": 50
    },
    "pro": {
        "variants_per_month": 100,
        "recipes_imported_per_month": 50,
        "cooking_sessions_per_month": 500
    },
    "enterprise": {
        "variants_per_month": -1,  # Unlimited
        "recipes_imported_per_month": -1,
        "cooking_sessions_per_month": -1
    }
}

STRIPE_PRICES = {
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly"),
    "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_pro_yearly"),
}


@router.get("/plan")
async def get_billing_plan(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Get user's current plan and daily variant usage."""
    # Get subscription
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    plan = subscription.plan if subscription else "free"
    limit = DAILY_VARIANT_QUOTAS.get(plan, DAILY_VARIANT_QUOTAS["free"])
    used = await get_daily_variant_usage(current_user.id, session)

    return {
        "plan": plan,
        "dailyVariantQuotaUsed": used,
        "limits": {
            "daily_variants": limit,
            "remaining": max(0, limit - used)
        },
        "subscription_status": subscription.status if subscription else "active"
    }


@router.post("/checkout-session")
async def create_checkout_session(
    interval: str,  # "monthly" or "yearly"
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Create Stripe checkout session for Pro plan subscription.

    Args:
        interval: "monthly" or "yearly" billing interval
        current_user: Authenticated user
        session: Database session

    Returns:
        checkout_url: Stripe hosted checkout page URL
    """
    # Validate interval
    if interval not in ["monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Interval must be 'monthly' or 'yearly'")

    # Get the appropriate price ID
    price_key = "pro_monthly" if interval == "monthly" else "pro_yearly"
    price_id = STRIPE_PRICES.get(price_key)

    if not price_id or price_id.startswith("price_pro"):
        # Price IDs not configured
        return {
            "checkout_url": f"https://checkout.stripe.com/stub?plan={interval}",
            "message": "Stripe not configured. Add STRIPE_PRICE_PRO and STRIPE_PRICE_PRO_YEAR to .env"
        }

    # Get or create Stripe customer
    customer_id = current_user.stripe_customer_id

    if not customer_id:
        # Create Stripe customer
        try:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.name,
                metadata={"user_id": str(current_user.id)}
            )
            customer_id = customer.id

            # Update user with customer ID
            current_user.stripe_customer_id = customer_id
            session.add(current_user)
            await session.commit()
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Failed to create customer: {str(e)}")

    # Create checkout session
    try:
        success_url = os.getenv("FRONTEND_URL", "http://localhost:5173") + "/settings/billing?success=true"
        cancel_url = os.getenv("FRONTEND_URL", "http://localhost:5173") + "/settings/billing?canceled=true"

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(current_user.id)
            }
        )

        return {
            "checkout_url": checkout_session.url
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.get("/portal")
async def get_customer_portal(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get Stripe customer portal URL for managing subscription.

    Args:
        current_user: Authenticated user

    Returns:
        portal_url: URL to Stripe customer portal
    """
    customer_id = current_user.stripe_customer_id

    if not customer_id:
        return {
            "portal_url": "https://billing.stripe.com/stub",
            "message": "No Stripe customer found. Subscribe to a plan first."
        }

    try:
        return_url = os.getenv("FRONTEND_URL", "http://localhost:5173") + "/settings/billing"

        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        return {
            "portal_url": portal_session.url
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.get("/subscription", response_model=SubscriptionRead)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> Subscription:
    """Get current user's subscription status."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        # Create free subscription if none exists
        now = datetime.utcnow()
        subscription = Subscription(
            user_id=current_user.id,
            plan="free",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=365),
            cancel_at_period_end=False
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)

    return subscription


@router.post("/create-checkout-session")
async def create_checkout_session(
    price_id: str,
    success_url: str,
    cancel_url: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Create Stripe checkout session for subscription."""

    # Get or create Stripe customer
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    customer_id = subscription.stripe_customer_id if subscription else None

    if not customer_id:
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"user_id": str(current_user.id)}
        )
        customer_id = customer.id

    # Create checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(current_user.id)
            }
        )

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Handle Stripe webhook events."""

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Log the event to billing_events table
    billing_event = BillingEvent(
        event_type=event.type,
        stripe_event_id=event.id,
        event_data=json.dumps(event.to_dict()),
        processed=False
    )
    session.add(billing_event)
    await session.commit()

    # Handle the event
    try:
        if event.type == "checkout.session.completed":
            checkout_session = event.data.object
            await _handle_checkout_completed(checkout_session, session, billing_event.id)

        elif event.type == "customer.subscription.updated":
            subscription_data = event.data.object
            await _handle_subscription_updated(subscription_data, session, billing_event.id)

        elif event.type == "customer.subscription.deleted":
            subscription_data = event.data.object
            await _handle_subscription_deleted(subscription_data, session, billing_event.id)

        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            await _handle_payment_failed(invoice, session, billing_event.id)

        # Mark event as processed
        billing_event.processed = True
        billing_event.processed_at = datetime.utcnow()
        await session.commit()

    except Exception as e:
        # Log error
        billing_event.error_message = str(e)
        await session.commit()
        raise

    return {"status": "success"}


async def _handle_checkout_completed(checkout_session: dict, session: AsyncSession, event_id):
    """Handle successful checkout completion."""
    user_id = checkout_session.get("metadata", {}).get("user_id")
    if not user_id:
        return

    # Get subscription details from Stripe
    subscription_id = checkout_session.subscription
    stripe_subscription = stripe.Subscription.retrieve(subscription_id)

    # Update or create subscription in database
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.plan = "pro"
        subscription.status = stripe_subscription.status
        subscription.stripe_subscription_id = stripe_subscription.id
        subscription.stripe_customer_id = stripe_subscription.customer
        subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
    else:
        subscription = Subscription(
            user_id=user_id,
            plan="pro",
            status=stripe_subscription.status,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=stripe_subscription.customer,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
        )
        session.add(subscription)

    await session.commit()


async def _handle_subscription_updated(subscription_data: dict, session: AsyncSession, event_id):
    """Handle subscription update events."""
    subscription_id = subscription_data.get("id")

    result = await session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = subscription_data.status
        subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)
        subscription.cancel_at_period_end = subscription_data.cancel_at_period_end
        await session.commit()


async def _handle_subscription_deleted(subscription_data: dict, session: AsyncSession, event_id):
    """Handle subscription cancellation."""
    subscription_id = subscription_data.get("id")

    result = await session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = "canceled"
        subscription.plan = "free"
        await session.commit()


async def _handle_payment_failed(invoice: dict, session: AsyncSession, event_id):
    """Handle failed payment."""
    customer_id = invoice.get("customer")

    result = await session.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = "past_due"
        await session.commit()


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Cancel user's subscription."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        # Cancel at period end (don't immediately cancel)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        subscription.cancel_at_period_end = True
        await session.commit()

        return {
            "message": "Subscription will be canceled at the end of the billing period",
            "cancel_at": subscription.current_period_end
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage", response_model=UsageRead)
async def get_usage(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> Usage:
    """Get current usage statistics for billing."""
    # Get current period (YYYY-MM)
    period = datetime.utcnow().strftime("%Y-%m")

    result = await session.execute(
        select(Usage).where(
            Usage.user_id == current_user.id,
            Usage.period == period
        )
    )
    usage = result.scalar_one_or_none()

    if not usage:
        # Create usage record for this period
        usage = Usage(
            user_id=current_user.id,
            period=period,
            variants_generated=0,
            recipes_imported=0,
            cooking_sessions=0
        )
        session.add(usage)
        await session.commit()
        await session.refresh(usage)

    return usage


@router.get("/limits")
async def get_plan_limits(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Get plan limits and current usage."""
    # Get subscription
    sub_result = await session.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = sub_result.scalar_one_or_none()
    plan = subscription.plan if subscription else "free"

    # Get usage
    period = datetime.utcnow().strftime("%Y-%m")
    usage_result = await session.execute(
        select(Usage).where(
            Usage.user_id == current_user.id,
            Usage.period == period
        )
    )
    usage = usage_result.scalar_one_or_none()

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    return {
        "plan": plan,
        "limits": limits,
        "usage": {
            "variants_generated": usage.variants_generated if usage else 0,
            "recipes_imported": usage.recipes_imported if usage else 0,
            "cooking_sessions": usage.cooking_sessions if usage else 0
        },
        "remaining": {
            "variants": limits["variants_per_month"] - (usage.variants_generated if usage else 0)
                if limits["variants_per_month"] != -1 else -1,
            "recipes": limits["recipes_imported_per_month"] - (usage.recipes_imported if usage else 0)
                if limits["recipes_imported_per_month"] != -1 else -1,
            "sessions": limits["cooking_sessions_per_month"] - (usage.cooking_sessions if usage else 0)
                if limits["cooking_sessions_per_month"] != -1 else -1
        }
    }


async def check_usage_limit(
    user: User,
    feature: str,
    session: AsyncSession
) -> bool:
    """
    Check if user has exceeded usage limits for a feature.

    Args:
        user: Current user
        feature: Feature name (variants, recipes, sessions)
        session: Database session

    Returns:
        True if within limits, False if exceeded
    """
    # Get subscription
    sub_result = await session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = sub_result.scalar_one_or_none()
    plan = subscription.plan if subscription else "free"

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Unlimited plans
    if limits.get(f"{feature}_per_month") == -1:
        return True

    # Get current usage
    period = datetime.utcnow().strftime("%Y-%m")
    usage_result = await session.execute(
        select(Usage).where(
            Usage.user_id == user.id,
            Usage.period == period
        )
    )
    usage = usage_result.scalar_one_or_none()

    if not usage:
        return True  # No usage yet, so within limits

    feature_map = {
        "variants": usage.variants_generated,
        "recipes": usage.recipes_imported,
        "sessions": usage.cooking_sessions
    }

    current_usage = feature_map.get(feature, 0)
    limit = limits.get(f"{feature}_per_month", 0)

    return current_usage < limit


async def increment_usage(
    user: User,
    feature: str,
    session: AsyncSession,
    amount: int = 1
):
    """
    Increment usage counter for a feature.

    Args:
        user: Current user
        feature: Feature name (variants, recipes, sessions)
        session: Database session
        amount: Amount to increment by
    """
    period = datetime.utcnow().strftime("%Y-%m")

    result = await session.execute(
        select(Usage).where(
            Usage.user_id == user.id,
            Usage.period == period
        )
    )
    usage = result.scalar_one_or_none()

    if not usage:
        usage = Usage(
            user_id=user.id,
            period=period,
            variants_generated=0,
            recipes_imported=0,
            cooking_sessions=0
        )
        session.add(usage)

    # Increment the appropriate counter
    if feature == "variants":
        usage.variants_generated += amount
    elif feature == "recipes":
        usage.recipes_imported += amount
    elif feature == "sessions":
        usage.cooking_sessions += amount

    await session.commit()

