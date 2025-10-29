"""
Test household invitation flow (Phase 5.2)

Tests the complete household invitation and onboarding flow:
- Owner creates invitation
- New member redeems token
- Member joins household
- Member can view their households
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tasteos_api.models.user import User
from tasteos_api.models.household import Household


pytestmark = pytest.mark.phase5


@pytest.mark.asyncio
async def test_household_invite_and_join_flow(
    async_client: AsyncClient,
    async_client_as_second_user: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_household: Household,
    second_user: User,
):
    """
    Test the complete invitation flow:
    1. test_user (owner) creates an invitation
    2. second_user redeems the token
    3. second_user joins the household
    4. second_user can see the household in /mine
    """
    
    # 1. test_user should already be owner of test_household (from fixture)
    # Create an invitation as test_user (owner)
    invite_payload = {
        "invited_email": "new_member@example.com",
        "role": "member"
    }
    
    res_invite = await async_client.post(
        "/api/v1/households/invite",
        json=invite_payload
    )
    assert res_invite.status_code == 201, f"Expected 201, got {res_invite.status_code}: {res_invite.text}"
    
    invite_data = res_invite.json()
    assert "token" in invite_data
    assert "household_id" in invite_data
    
    token = invite_data["token"]
    assert len(token) > 0
    assert invite_data["household_id"] == str(test_household.id)
    
    # 2. Now act as second_user and join via token
    join_payload = {
        "token": token
    }
    
    res_join = await async_client_as_second_user.post(
        "/api/v1/households/join",
        json=join_payload
    )
    assert res_join.status_code == 200, f"Expected 200, got {res_join.status_code}: {res_join.text}"
    
    join_data = res_join.json()
    assert join_data["status"] == "joined"
    assert join_data["role"] == "member"
    assert join_data["household_id"] == str(test_household.id)
    
    # 3. Verify second_user can see the household in /mine
    res_mine = await async_client_as_second_user.get("/api/v1/households/mine")
    assert res_mine.status_code == 200
    
    mine_data = res_mine.json()
    assert isinstance(mine_data, list)
    assert len(mine_data) > 0
    
    # Check that test_household is in the list
    household_ids = [h["household_id"] for h in mine_data]
    assert str(test_household.id) in household_ids
    
    # Find the household and verify details
    household_entry = next(
        (h for h in mine_data if h["household_id"] == str(test_household.id)),
        None
    )
    assert household_entry is not None
    assert household_entry["name"] == test_household.name
    assert household_entry["role"] == "member"


@pytest.mark.asyncio
async def test_invite_requires_owner_role(
    async_client_as_second_user: AsyncClient,
    db_session: AsyncSession,
    test_household: Household,
    second_user: User,
    attach_second_user_to_household,  # second_user is a "member", not "owner"
):
    """
    Test that only owners can create invitations.
    second_user is a member (not owner) and should get 403.
    """
    
    invite_payload = {
        "invited_email": "someone@example.com",
        "role": "member"
    }
    
    res = await async_client_as_second_user.post(
        "/api/v1/households/invite",
        json=invite_payload
    )
    
    assert res.status_code == 403
    assert "owner" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_reuse_accepted_token(
    async_client: AsyncClient,
    async_client_as_second_user: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_household: Household,
    second_user: User,
):
    """
    Test that a token can only be used once.
    After second_user joins, attempting to use the same token should fail.
    """
    
    # 1. Create invitation
    invite_payload = {
        "invited_email": "someone@example.com",
        "role": "member"
    }
    
    res_invite = await async_client.post(
        "/api/v1/households/invite",
        json=invite_payload
    )
    assert res_invite.status_code == 201
    token = res_invite.json()["token"]
    
    # 2. Use token once (should succeed)
    join_payload = {"token": token}
    res_join1 = await async_client_as_second_user.post(
        "/api/v1/households/join",
        json=join_payload
    )
    assert res_join1.status_code == 200
    
    # 3. Try to use the same token again (should fail with 410 Gone)
    res_join2 = await async_client_as_second_user.post(
        "/api/v1/households/join",
        json=join_payload
    )
    assert res_join2.status_code == 410
    assert "already been used" in res_join2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_token_returns_404(
    async_client_as_second_user: AsyncClient,
):
    """
    Test that an invalid token returns 404.
    """
    
    join_payload = {"token": "invalid-token-that-does-not-exist"}
    
    res = await async_client_as_second_user.post(
        "/api/v1/households/join",
        json=join_payload
    )
    
    assert res.status_code == 404
    assert "invalid" in res.json()["detail"].lower()
