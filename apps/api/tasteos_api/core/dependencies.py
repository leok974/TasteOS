"""
Authentication dependencies for protected routes.

This module provides dependency functions for authenticating users
and should be imported by routers that need authentication.
"""

from types import SimpleNamespace
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.auth import decode_access_token
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.household import Household, HouseholdMembership

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Get current authenticated user from JWT token.

    This dependency can be used in any router that requires authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    # Convert string to UUID
    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise credentials_exception

    # Get user from database
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_household(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SimpleNamespace:
    """
    Resolve the active household for this request.

    Phase 4 version: picks the first household the user belongs to.
    Later we'll support explicit household selection via headers/query params.

    Returns:
        SimpleNamespace with id and name attributes

    Raises:
        HTTPException: 403 if user is not in any household
    """
    # Get first household membership for user
    result = await session.exec(
        select(Household)
        .join(HouseholdMembership)
        .where(HouseholdMembership.user_id == current_user.id)
        .order_by(HouseholdMembership.joined_at)
    )
    household = result.first()

    if not household:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not in any household",
        )

    # Return lightweight household context
    return SimpleNamespace(id=household.id, name=household.name)
