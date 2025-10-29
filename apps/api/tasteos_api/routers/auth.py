"""
Authentication router for user management.

This module provides endpoints for user registration, login,
and JWT token management with cookie-based session support.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from tasteos_api.core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from tasteos_api.core.database import get_db_session
from tasteos_api.core.dependencies import get_current_user
from tasteos_api.models.user import User, UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Register a new user account."""
    # Check if user already exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        plan=user_data.plan,
        is_active=user_data.is_active,
        subscription_status=user_data.subscription_status,
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user


@router.post("/login")
async def login(
    response: Response,
    payload: dict,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str | UserRead]:
    """
    Authenticate user and return JWT token + set session cookie.

    Accepts JSON body:
    {
      "email": "user@example.com",
      "password": "secret123"
    }
    """
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password required"
        )

    # Get user from database
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # Set cookie for browser-based auth (24 hours)
    response.set_cookie(
        key="tasteos_session",
        value=access_token,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24,  # 24 hours
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user)
    }


@router.post("/login/token")
async def login_oauth(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str | UserRead]:
    """
    OAuth2-compatible login endpoint (for API clients).
    Uses form data instead of JSON.
    """
    # Get user from database
    result = await session.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # Set cookie for browser-based auth
    response.set_cookie(
        key="tasteos_session",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user)
    }


@router.post("/refresh")
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Refresh JWT token."""
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current authenticated user profile."""
    return current_user


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout by clearing the session cookie."""
    response.delete_cookie(key="tasteos_session")
    return {"status": "ok", "message": "Logged out successfully"}
