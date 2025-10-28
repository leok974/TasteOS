"""
Shopping router for TasteOS API.

Endpoints for managing shopping lists derived from meal plans.
"""

import json
import csv
import io
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.grocery_item import (
    GroceryItem,
    GroceryItemCreate,
    GroceryItemRead
)
from tasteos_api.models.meal_plan import MealPlan
from tasteos_api.models.pantry_item import PantryItem
from tasteos_api.agents import shopping_agent


router = APIRouter(prefix="/shopping", tags=["shopping"])


@router.post("/generate", response_model=List[GroceryItemRead])
async def generate_shopping_list(
    plan_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[GroceryItemRead]:
    """
    Generate a shopping list from a meal plan.

    Compares meal plan requirements against pantry inventory
    and creates grocery items for missing ingredients.

    Args:
        plan_id: UUID of the meal plan to generate list from

    Returns:
        List of created grocery items
    """
    # Get the meal plan
    plan_result = await session.execute(
        select(MealPlan)
        .where(MealPlan.id == plan_id)
        .where(MealPlan.user_id == current_user.id)
    )
    meal_plan = plan_result.scalar_one_or_none()

    if not meal_plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    # Get pantry items
    pantry_result = await session.execute(
        select(PantryItem).where(PantryItem.user_id == current_user.id)
    )
    pantry_items = pantry_result.scalars().all()

    # Convert to dict format
    meal_plan_data = {
        "breakfast": json.loads(meal_plan.breakfast) if isinstance(meal_plan.breakfast, str) else meal_plan.breakfast,
        "lunch": json.loads(meal_plan.lunch) if isinstance(meal_plan.lunch, str) else meal_plan.lunch,
        "dinner": json.loads(meal_plan.dinner) if isinstance(meal_plan.dinner, str) else meal_plan.dinner,
        "snacks": json.loads(meal_plan.snacks) if isinstance(meal_plan.snacks, str) else meal_plan.snacks,
    }

    pantry_data = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit
        }
        for item in pantry_items
    ]

    # Call shopping agent
    shopping_list = await shopping_agent.plan_to_list(
        meal_plan=meal_plan_data,
        pantry_items=pantry_data
    )

    # Save grocery items
    created_items = []

    for item_data in shopping_list:
        grocery_item = GroceryItem(
            user_id=current_user.id,
            meal_plan_id=plan_id,
            name=item_data["name"],
            quantity=item_data.get("quantity"),
            unit=item_data.get("unit"),
            purchased=False
        )

        session.add(grocery_item)
        await session.flush()
        await session.refresh(grocery_item)

        created_items.append(GroceryItemRead(
            id=grocery_item.id,
            user_id=grocery_item.user_id,
            meal_plan_id=grocery_item.meal_plan_id,
            name=grocery_item.name,
            quantity=grocery_item.quantity,
            unit=grocery_item.unit,
            purchased=grocery_item.purchased,
            created_at=grocery_item.created_at,
            updated_at=grocery_item.updated_at
        ))

    await session.commit()

    return created_items


@router.get("/", response_model=List[GroceryItemRead])
async def get_shopping_list(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[GroceryItemRead]:
    """
    Get all grocery items for the current user.

    Returns items grouped by meal_plan_id (in the client).
    """
    result = await session.execute(
        select(GroceryItem)
        .where(GroceryItem.user_id == current_user.id)
        .order_by(GroceryItem.purchased, GroceryItem.created_at.desc())
    )
    items = result.scalars().all()

    return [
        GroceryItemRead(
            id=item.id,
            user_id=item.user_id,
            meal_plan_id=item.meal_plan_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            purchased=item.purchased,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        for item in items
    ]


@router.post("/{item_id}/toggle")
async def toggle_purchased(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GroceryItemRead:
    """
    Toggle the purchased status of a grocery item.

    Args:
        item_id: UUID of the grocery item

    Returns:
        Updated grocery item
    """
    result = await session.execute(
        select(GroceryItem)
        .where(GroceryItem.id == item_id)
        .where(GroceryItem.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Grocery item not found")

    # Toggle purchased status
    item.purchased = not item.purchased

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return GroceryItemRead(
        id=item.id,
        user_id=item.user_id,
        meal_plan_id=item.meal_plan_id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        purchased=item.purchased,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.post("/export")
async def export_shopping_list(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """
    Export shopping list as CSV.

    Returns:
        CSV file with grocery items
    """
    result = await session.execute(
        select(GroceryItem)
        .where(GroceryItem.user_id == current_user.id)
        .where(GroceryItem.purchased == False)
        .order_by(GroceryItem.name)
    )
    items = result.scalars().all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Item", "Quantity", "Unit", "Purchased"])

    # Data
    for item in items:
        writer.writerow([
            item.name,
            item.quantity if item.quantity is not None else "",
            item.unit if item.unit else "",
            "Yes" if item.purchased else "No"
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=shopping_list.csv"
        }
    )
