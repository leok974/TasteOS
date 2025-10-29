"""
Pantry router for TasteOS API.

Endpoints for managing user's pantry inventory.
"""

import json
from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user, get_current_household
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.pantry_item import (
    PantryItem,
    PantryItemCreate,
    PantryItemRead,
    PantryItemUpdate
)
from tasteos_api.agents import pantry_agent


router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.get("/", response_model=List[PantryItemRead])
async def get_pantry(
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[PantryItemRead]:
    """
    Get all pantry items for the current household.

    Returns a list of items with quantities, units, expiration dates, and tags.
    Phase 4: Scoped by household instead of individual user.
    """
    result = await session.exec(
        select(PantryItem)
        .where(PantryItem.household_id == current_household.id)
        .order_by(PantryItem.created_at.desc())
    )
    items = result.all()

    return [
        PantryItemRead(
            id=item.id,
            user_id=item.user_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            expires_at=item.expires_at,
            tags=json.loads(item.tags) if isinstance(item.tags, str) else item.tags,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        for item in items
    ]


@router.post("/", response_model=PantryItemRead)
async def add_pantry_item(
    data: PantryItemCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PantryItemRead:
    """
    Add a new item to the pantry.

    If an item with the same name already exists, updates the quantity instead.
    This implements upsert logic for pantry management.
    Phase 4: Scoped by household.
    """
    # Check if item already exists
    result = await session.exec(
        select(PantryItem)
        .where(PantryItem.household_id == current_household.id)
        .where(PantryItem.name == data.name)
    )
    existing_item = result.first()

    if existing_item:
        # Update existing item (upsert)
        if data.quantity is not None:
            existing_item.quantity = data.quantity
        if data.unit is not None:
            existing_item.unit = data.unit
        if data.expires_at is not None:
            existing_item.expires_at = data.expires_at
        if data.tags:
            existing_item.tags = json.dumps(data.tags)

        existing_item.updated_at = datetime.utcnow()

        session.add(existing_item)
        await session.commit()
        await session.refresh(existing_item)

        return PantryItemRead(
            id=existing_item.id,
            user_id=existing_item.user_id,
            name=existing_item.name,
            quantity=existing_item.quantity,
            unit=existing_item.unit,
            expires_at=existing_item.expires_at,
            tags=json.loads(existing_item.tags) if isinstance(existing_item.tags, str) else existing_item.tags,
            created_at=existing_item.created_at,
            updated_at=existing_item.updated_at
        )

    # Create new item
    new_item = PantryItem(
        user_id=current_user.id,
        household_id=current_household.id,
        added_by_user_id=current_user.id,
        name=data.name,
        quantity=data.quantity,
        unit=data.unit,
        expires_at=data.expires_at,
        tags=json.dumps(data.tags) if data.tags else "[]"
    )

    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)

    return PantryItemRead(
        id=new_item.id,
        user_id=new_item.user_id,
        name=new_item.name,
        quantity=new_item.quantity,
        unit=new_item.unit,
        expires_at=new_item.expires_at,
        tags=json.loads(new_item.tags) if isinstance(new_item.tags, str) else new_item.tags,
        created_at=new_item.created_at,
        updated_at=new_item.updated_at
    )


@router.delete("/{item_id}")
async def delete_pantry_item(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """
    Delete an item from the pantry.
    Phase 4: Household-scoped, returns 404 if not in household.
    """
    result = await session.exec(
        select(PantryItem)
        .where(PantryItem.id == item_id)
        .where(PantryItem.household_id == current_household.id)
    )
    item = result.first()

    if not item:
        raise HTTPException(status_code=404, detail="Pantry item not found")

    await session.delete(item)
    await session.commit()

    return {"status": "success", "message": "Item deleted"}


@router.post("/scan")
async def scan_pantry_item(
    barcode: Optional[str] = None,
    raw_text: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Parse pantry item from barcode or raw text.

    This uses AI to interpret natural language descriptions like:
    - "half an onion"
    - "2 lbs chicken breast"
    - "3 eggs"

    Returns a draft PantryItem that can be saved via POST /pantry.
    """
    if not barcode and not raw_text:
        raise HTTPException(
            status_code=400,
            detail="Either barcode or raw_text must be provided"
        )

    # Call pantry agent to parse
    parsed_data = await pantry_agent.parse_item(barcode=barcode, raw_text=raw_text)

    return {
        "draft_item": parsed_data,
        "message": "Parsed successfully. Send to POST /pantry to save."
    }
