"""
Meal planner router for TasteOS API.

Endpoints for AI-powered meal planning.
"""

import json
from typing import Annotated, List
from uuid import UUID, uuid4
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user, get_current_household
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.meal_plan import (
    MealPlan,
    MealPlanRead,
    GeneratePlanRequest,
    GeneratePlanResponse
)
from tasteos_api.models.pantry_item import PantryItem
from tasteos_api.agents import planner_agent


router = APIRouter(prefix="/planner", tags=["planner"])


@router.post("/generate", response_model=GeneratePlanResponse)
async def generate_meal_plan(
    request: GeneratePlanRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GeneratePlanResponse:
    """
    Generate a multi-day meal plan using AI.

    Takes nutrition goals, dietary preferences, and budget constraints,
    then creates a personalized meal plan that uses pantry inventory.
    Phase 4: Scoped by household.

    Args:
        request: Plan parameters including days, goals, preferences

    Returns:
        Generated plan with IDs and summary
    """

    # Get household's pantry items
    pantry_result = await session.exec(
        select(PantryItem).where(PantryItem.household_id == current_household.id)
    )
    pantry_items = pantry_result.all()

    # Convert to dict format for agent
    pantry_data = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
            "tags": json.loads(item.tags) if isinstance(item.tags, str) else item.tags
        }
        for item in pantry_items
    ]

    # Call planner agent
    plan_data = await planner_agent.generate_week_plan(
        pantry_items=pantry_data,
        goals=request.goals,
        prefs={
            "days": request.days,
            "dietary_preferences": request.dietary_preferences,
            "budget": request.budget
        }
    )

    # Save to database
    batch_id = uuid4()
    plan_ids = []

    for day_plan in plan_data:
        meal_plan = MealPlan(
            user_id=current_user.id,
            household_id=current_household.id,
            date=datetime.fromisoformat(day_plan["date"]).date(),
            breakfast=json.dumps(day_plan.get("breakfast", [])),
            lunch=json.dumps(day_plan.get("lunch", [])),
            dinner=json.dumps(day_plan.get("dinner", [])),
            snacks=json.dumps(day_plan.get("snacks", [])),
            notes_per_user=json.dumps(day_plan.get("notes_per_user", {})),
            total_calories=day_plan.get("total_calories"),
            total_protein_g=day_plan.get("total_protein_g"),
            total_carbs_g=day_plan.get("total_carbs_g"),
            total_fat_g=day_plan.get("total_fat_g"),
            notes=day_plan.get("notes"),
            plan_batch_id=batch_id
        )

        session.add(meal_plan)
        await session.flush()
        await session.refresh(meal_plan)
        plan_ids.append(str(meal_plan.id))

    await session.commit()

    # Generate summary
    summary = f"Generated {request.days}-day meal plan"
    if request.dietary_preferences:
        summary += f" with {', '.join(request.dietary_preferences)} preferences"

    start_date = plan_data[0]["date"] if plan_data else date.today().isoformat()

    return GeneratePlanResponse(
        plan_ids=plan_ids,
        summary=summary,
        start_date=start_date
    )


@router.get("/today", response_model=MealPlanRead)
async def get_today_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MealPlanRead:
    """
    Get the meal plan for today.
    Phase 4: Scoped by household.

    Returns:
        Today's meal plan with all meals

    Raises:
        404: If no plan exists for today
    """
    today = date.today()

    result = await session.exec(
        select(MealPlan)
        .where(MealPlan.household_id == current_household.id)
        .where(MealPlan.date == today)
    )
    plan = result.first()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="No meal plan found for today"
        )

    return MealPlanRead(
        id=plan.id,
        user_id=plan.user_id,
        date=plan.date,
        breakfast=json.loads(plan.breakfast) if isinstance(plan.breakfast, str) else plan.breakfast,
        lunch=json.loads(plan.lunch) if isinstance(plan.lunch, str) else plan.lunch,
        dinner=json.loads(plan.dinner) if isinstance(plan.dinner, str) else plan.dinner,
        snacks=json.loads(plan.snacks) if isinstance(plan.snacks, str) else plan.snacks,
        total_calories=plan.total_calories,
        total_protein_g=plan.total_protein_g,
        total_carbs_g=plan.total_carbs_g,
        total_fat_g=plan.total_fat_g,
        notes=plan.notes,
        plan_batch_id=plan.plan_batch_id,
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )


@router.get("/{plan_id}", response_model=MealPlanRead)
async def get_meal_plan(
    plan_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MealPlanRead:
    """
    Get a specific meal plan by ID.
    Phase 4: Household-scoped, returns 404 if not in household.

    Args:
        plan_id: UUID of the meal plan

    Returns:
        The meal plan with all details

    Raises:
        404: If plan not found or not owned by household
    """
    result = await session.exec(
        select(MealPlan)
        .where(MealPlan.id == plan_id)
        .where(MealPlan.household_id == current_household.id)
    )
    plan = result.first()

    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    return MealPlanRead(
        id=plan.id,
        user_id=plan.user_id,
        date=plan.date,
        breakfast=json.loads(plan.breakfast) if isinstance(plan.breakfast, str) else plan.breakfast,
        lunch=json.loads(plan.lunch) if isinstance(plan.lunch, str) else plan.lunch,
        dinner=json.loads(plan.dinner) if isinstance(plan.dinner, str) else plan.dinner,
        snacks=json.loads(plan.snacks) if isinstance(plan.snacks, str) else plan.snacks,
        total_calories=plan.total_calories,
        total_protein_g=plan.total_protein_g,
        total_carbs_g=plan.total_carbs_g,
        total_fat_g=plan.total_fat_g,
        notes=plan.notes,
        plan_batch_id=plan.plan_batch_id,
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )
