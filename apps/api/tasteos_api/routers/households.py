"""
Households router for TasteOS API.

Handles household invitation and management.
"""

from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from tasteos_api.core.database import get_db_session
from tasteos_api.core.dependencies import get_current_user, get_current_household
from tasteos_api.models.household import Household, HouseholdMembership
from tasteos_api.models.household_invite import (
    HouseholdInvite,
    HouseholdInviteCreate,
    HouseholdInviteToken,
)
from tasteos_api.models.user import User


router = APIRouter(prefix="", tags=["households"])


async def _require_owner(
    db: AsyncSession,
    user_id: int,
    household_id: int,
) -> HouseholdMembership:
    """
    Helper to verify that a user is an owner of a household.

    Args:
        db: Database session
        user_id: User ID to check
        household_id: Household ID to check ownership for

    Returns:
        The HouseholdMembership record

    Raises:
        HTTPException: If user is not an owner (403)
    """
    q = select(HouseholdMembership).where(
        HouseholdMembership.user_id == user_id,
        HouseholdMembership.household_id == household_id,
    )
    res = await db.exec(q)
    membership = res.first()

    if not membership or membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only owners can perform this action.",
        )

    return membership


@router.post("/invite", response_model=HouseholdInviteToken, status_code=201)
async def create_household_invite(
    invite_data: HouseholdInviteCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[Household, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HouseholdInviteToken:
    """
    Create an invitation to join the current household.

    Only household owners can create invitations.
    Returns a secure token that can be redeemed by the invitee.

    Args:
        invite_data: Email and role for the invitee
        current_user: Authenticated user (must be owner)
        current_household: Current household context
        session: Database session

    Returns:
        Token and household_id for the invitation

    Raises:
        HTTPException: If user is not an owner
    """
    # Verify current_user is an owner of current_household
    await _require_owner(session, current_user.id, current_household.id)

    # Validate role
    if invite_data.role not in ("owner", "member"):
        raise HTTPException(
            status_code=400,
            detail="Role must be 'owner' or 'member'"
        )

    # Create the invite
    invite = HouseholdInvite(
        household_id=current_household.id,
        invited_email=invite_data.invited_email,
        role=invite_data.role,
        token=HouseholdInvite.generate_token(),
        revoked=False,
    )

    session.add(invite)
    await session.commit()
    await session.refresh(invite)

    return HouseholdInviteToken(
        token=invite.token,
        household_id=invite.household_id,
    )


@router.post("/join")
async def join_household_via_invite(
    token_data: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """
    Join a household using an invitation token.

    Redeems an invitation token and creates a household membership.

    Args:
        token_data: Dictionary containing the invitation token
        current_user: Authenticated user joining the household
        session: Database session

    Returns:
        Status information about the join operation

    Raises:
        HTTPException: If token is invalid, already used, or revoked
    """
    token = token_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    # Look up the invite
    invite_query = select(HouseholdInvite).where(
        HouseholdInvite.token == token
    )
    invite_result = await session.exec(invite_query)
    invite = invite_result.first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    # Check if already accepted
    if invite.accepted_at is not None:
        raise HTTPException(
            status_code=410,
            detail="This invitation has already been used"
        )

    # Check if revoked
    if invite.revoked:
        raise HTTPException(
            status_code=403,
            detail="This invitation has been revoked"
        )

    # Check if user is already a member
    existing_membership_query = select(HouseholdMembership).where(
        HouseholdMembership.household_id == invite.household_id,
        HouseholdMembership.user_id == current_user.id,
    )
    existing_membership_result = await session.exec(existing_membership_query)
    existing_membership = existing_membership_result.first()

    if existing_membership:
        raise HTTPException(
            status_code=400,
            detail="You are already a member of this household"
        )

    # Create the membership
    membership = HouseholdMembership(
        household_id=invite.household_id,
        user_id=current_user.id,
        role=invite.role,
    )

    session.add(membership)

    # Mark invite as accepted
    invite.accepted_at = datetime.utcnow()
    session.add(invite)

    await session.commit()
    await session.refresh(membership)

    return {
        "household_id": str(membership.household_id),
        "role": membership.role,
        "status": "joined",
    }


@router.get("/mine")
async def get_my_households(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[dict]:
    """
    Get all households the current user belongs to.

    Returns a list of households with the user's role in each.

    Args:
        current_user: Authenticated user
        session: Database session

    Returns:
        List of households with id, name, and role
    """
    # Get all memberships for the user
    memberships_query = select(HouseholdMembership).where(
        HouseholdMembership.user_id == current_user.id
    )
    memberships_result = await session.exec(memberships_query)
    memberships = memberships_result.all()

    # Fetch household details for each membership
    households = []
    for membership in memberships:
        household_query = select(Household).where(
            Household.id == membership.household_id
        )
        household_result = await session.exec(household_query)
        household = household_result.first()

        if household:
            households.append({
                "household_id": str(household.id),
                "name": household.name,
                "role": membership.role,
            })

    return households
