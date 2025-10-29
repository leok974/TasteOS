"""
Recipe Memory router for TasteOS API.

Endpoints for managing household recipe memories - cultural knowledge,
substitutions, and cooking preferences (Phase 4 - Family Mode).
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user, get_current_household
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.recipe_memory import (
    RecipeMemory,
    RecipeMemoryCreate,
    RecipeMemoryRead
)


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/", response_model=List[RecipeMemoryRead])
async def list_recipe_memory(
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[RecipeMemoryRead]:
    """
    List all recipe memories for the current household.

    Returns cultural knowledge, substitutions, and cooking preferences
    that have been saved by household members.
    """
    result = await session.exec(
        select(RecipeMemory)
        .where(RecipeMemory.household_id == current_household.id)
        .order_by(RecipeMemory.updated_at.desc())
    )
    memories = result.all()

    return [
        RecipeMemoryRead(
            id=memory.id,
            household_id=memory.household_id,
            dish_name=memory.dish_name,
            origin_notes=memory.origin_notes,
            substitutions=memory.substitutions,
            spice_prefs=memory.spice_prefs,
            last_cooked_at=memory.last_cooked_at,
            created_by_user=memory.created_by_user,
            created_at=memory.created_at,
            updated_at=memory.updated_at
        )
        for memory in memories
    ]


@router.post("/", response_model=RecipeMemoryRead, status_code=status.HTTP_201_CREATED)
async def create_recipe_memory(
    data: RecipeMemoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecipeMemoryRead:
    """
    Create a new recipe memory for the household.

    Captures cultural knowledge like:
    - Origin stories ("Sunday routine with family")
    - Ingredient substitutions ("coconut milk + heavy cream for sauce")
    - Spice preferences per family member
    - Last time the dish was cooked
    """
    memory = RecipeMemory(
        household_id=current_household.id,
        dish_name=data.dish_name,
        origin_notes=data.origin_notes,
        substitutions=data.substitutions,
        spice_prefs=data.spice_prefs,
        last_cooked_at=data.last_cooked_at,
        created_by_user=current_user.id
    )

    session.add(memory)
    await session.commit()
    await session.refresh(memory)

    return RecipeMemoryRead(
        id=memory.id,
        household_id=memory.household_id,
        dish_name=memory.dish_name,
        origin_notes=memory.origin_notes,
        substitutions=memory.substitutions,
        spice_prefs=memory.spice_prefs,
        last_cooked_at=memory.last_cooked_at,
        created_by_user=memory.created_by_user,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


@router.get("/{memory_id}", response_model=RecipeMemoryRead)
async def get_recipe_memory(
    memory_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecipeMemoryRead:
    """
    Get a specific recipe memory by ID.

    Returns 404 if not found or not in current household.
    """
    result = await session.exec(
        select(RecipeMemory)
        .where(RecipeMemory.id == memory_id)
        .where(RecipeMemory.household_id == current_household.id)
    )
    memory = result.first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe memory not found"
        )

    return RecipeMemoryRead(
        id=memory.id,
        household_id=memory.household_id,
        dish_name=memory.dish_name,
        origin_notes=memory.origin_notes,
        substitutions=memory.substitutions,
        spice_prefs=memory.spice_prefs,
        last_cooked_at=memory.last_cooked_at,
        created_by_user=memory.created_by_user,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_memory(
    memory_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """
    Delete a recipe memory.

    Returns 404 if not found or not in current household.
    """
    result = await session.exec(
        select(RecipeMemory)
        .where(RecipeMemory.id == memory_id)
        .where(RecipeMemory.household_id == current_household.id)
    )
    memory = result.first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe memory not found"
        )

    await session.delete(memory)
    await session.commit()
