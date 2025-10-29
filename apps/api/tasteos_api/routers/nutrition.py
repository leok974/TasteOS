"""
Nutrition endpoints for TasteOS API.

Provides endpoints to get nutritional information for recipes and variants.
Phase 5.1 adds user nutrition profiles and household nutrition evaluation.
"""

import json
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user, get_current_household
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.recipe import Recipe
from tasteos_api.models.variant import RecipeVariant
from tasteos_api.models.recipe_nutrition import RecipeNutrition, RecipeNutritionRead
from tasteos_api.models.user_nutrition_profile import (
    UserNutritionProfile,
    UserNutritionProfileCreate,
    UserNutritionProfileRead,
)
from tasteos_api.models.recipe_nutrition_info import RecipeNutritionInfo
from tasteos_api.models.recipe_memory import RecipeMemory
from tasteos_api.models.meal_plan import MealPlan
from tasteos_api.models.household import HouseholdMembership
from tasteos_api.agents import nutrition_analyzer


router = APIRouter(prefix="", tags=["nutrition"])


@router.get("/recipes/{recipe_id}/nutrition", response_model=RecipeNutritionRead)
async def get_recipe_nutrition(
    recipe_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecipeNutritionRead:
    """
    Get nutritional information for a recipe.

    This endpoint:
    - Looks up cached nutrition data
    - If not found, calculates it and caches the result
    - Returns calories, protein, carbs, fat per serving

    Args:
        recipe_id: ID of the recipe
        current_user: Authenticated user
        session: Database session

    Returns:
        Nutrition data with macros

    Raises:
        HTTPException: If recipe not found or not accessible
    """
    # Get the recipe
    result = await session.exec(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.first()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check ownership
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this recipe")

    # Check for cached nutrition
    nutrition_result = await session.exec(
        select(RecipeNutrition)
        .where(RecipeNutrition.recipe_id == recipe_id)
        .where(RecipeNutrition.variant_id == None)
    )
    cached_nutrition = nutrition_result.first()

    if cached_nutrition:
        return RecipeNutritionRead(
            calories=cached_nutrition.calories,
            protein_g=cached_nutrition.protein_g,
            carbs_g=cached_nutrition.carbs_g,
            fat_g=cached_nutrition.fat_g,
            notes=cached_nutrition.notes,
        )

    # Calculate nutrition if not cached
    recipe_data = {
        "title": recipe.title,
        "ingredients": json.loads(recipe.ingredients),
        "servings": recipe.servings,
    }

    nutrition_data = await nutrition_analyzer.analyze_recipe_macros(recipe_data)

    # Cache the result
    new_nutrition = RecipeNutrition(
        recipe_id=recipe_id,
        variant_id=None,
        calories=nutrition_data["calories"],
        protein_g=nutrition_data["protein_g"],
        carbs_g=nutrition_data["carbs_g"],
        fat_g=nutrition_data["fat_g"],
        notes=nutrition_data.get("notes"),
    )

    session.add(new_nutrition)
    await session.commit()

    return RecipeNutritionRead(
        calories=nutrition_data["calories"],
        protein_g=nutrition_data["protein_g"],
        carbs_g=nutrition_data["carbs_g"],
        fat_g=nutrition_data["fat_g"],
        notes=nutrition_data.get("notes"),
    )


@router.get("/variants/{variant_id}/nutrition", response_model=RecipeNutritionRead)
async def get_variant_nutrition(
    variant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecipeNutritionRead:
    """
    Get nutritional information for a variant.

    This endpoint:
    - Looks up cached nutrition data for the variant
    - If not found, calculates it based on variant changes
    - Returns calories, protein, carbs, fat per serving

    Args:
        variant_id: ID of the variant
        current_user: Authenticated user
        session: Database session

    Returns:
        Nutrition data with macros

    Raises:
        HTTPException: If variant not found or not accessible
    """
    # Get the variant
    result = await session.exec(
        select(RecipeVariant).where(RecipeVariant.id == variant_id)
    )
    variant = result.first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Get the base recipe to check ownership
    recipe_result = await session.exec(
        select(Recipe).where(Recipe.id == variant.recipe_id)
    )
    recipe = recipe_result.first()

    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this variant")

    # Check for cached nutrition
    nutrition_result = await session.exec(
        select(RecipeNutrition)
        .where(RecipeNutrition.variant_id == variant_id)
    )
    cached_nutrition = nutrition_result.first()

    if cached_nutrition:
        return RecipeNutritionRead(
            calories=cached_nutrition.calories,
            protein_g=cached_nutrition.protein_g,
            carbs_g=cached_nutrition.carbs_g,
            fat_g=cached_nutrition.fat_g,
            notes=cached_nutrition.notes,
        )

    # Calculate nutrition if not cached
    recipe_data = {
        "title": recipe.title,
        "ingredients": json.loads(recipe.ingredients),
        "servings": recipe.servings,
    }

    variant_data = {
        "variant_type": variant.variant_type,
        "ingredients": json.loads(variant.modified_ingredients),
    }

    nutrition_data = await nutrition_analyzer.analyze_recipe_macros(recipe_data, variant_data)

    # Cache the result
    new_nutrition = RecipeNutrition(
        recipe_id=variant.recipe_id,
        variant_id=variant_id,
        calories=nutrition_data["calories"],
        protein_g=nutrition_data["protein_g"],
        carbs_g=nutrition_data["carbs_g"],
        fat_g=nutrition_data["fat_g"],
        notes=nutrition_data.get("notes"),
    )

    session.add(new_nutrition)
    await session.commit()

    return RecipeNutritionRead(
        calories=nutrition_data["calories"],
        protein_g=nutrition_data["protein_g"],
        carbs_g=nutrition_data["carbs_g"],
        fat_g=nutrition_data["fat_g"],
        notes=nutrition_data.get("notes"),
    )



# Phase 5.1: User Nutrition Profiles & Household Evaluation


@router.get("/nutrition/profile", response_model=UserNutritionProfileRead)
async def get_nutrition_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Get nutrition profile for current user.

    Returns dietary goals, restrictions, and cultural notes.
    """
    result = await session.exec(
        select(UserNutritionProfile).where(
            UserNutritionProfile.user_id == current_user.id
        )
    )
    profile = result.first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Nutrition profile not found. Create one with POST /nutrition/profile"
        )

    return profile


@router.post("/nutrition/profile", response_model=UserNutritionProfileRead, status_code=201)
async def create_or_update_nutrition_profile(
    profile_data: UserNutritionProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Create or update nutrition profile for current user.

    Always uses current_user.id - clients cannot set profile for other users.
    """
    # Check if profile already exists
    result = await session.exec(
        select(UserNutritionProfile).where(
            UserNutritionProfile.user_id == current_user.id
        )
    )
    existing_profile = result.first()

    if existing_profile:
        # Update existing profile
        update_data = profile_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_profile, key, value)
        existing_profile.updated_at = datetime.utcnow()

        session.add(existing_profile)
        await session.commit()
        await session.refresh(existing_profile)

        return existing_profile

    # Create new profile
    new_profile = UserNutritionProfile(
        **profile_data.model_dump(exclude_none=True),
        user_id=current_user.id
    )

    session.add(new_profile)
    await session.commit()
    await session.refresh(new_profile)

    return new_profile


@router.get("/nutrition/today")
async def get_nutrition_today(
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Evaluate today's meal plan against household members' nutrition goals.

    Returns:
    - Summary of alignment
    - Per-user assessment (goals vs estimated)
    - Dietary restriction violations
    - Suggestions for modifications

    This is the "Health Mode" money endpoint.
    """
    today = date.today()

    # 1. Get today's meal plan for this household
    result = await session.exec(
        select(MealPlan)
        .where(MealPlan.household_id == current_household.id)
        .where(MealPlan.date == today)
    )
    meal_plan = result.first()

    if not meal_plan:
        return {
            "date": today.isoformat(),
            "household_id": str(current_household.id),
            "summary": "No meal plan for today",
            "per_user": {}
        }

    # 2. Get all household members
    result = await session.exec(
        select(HouseholdMembership).where(
            HouseholdMembership.household_id == current_household.id
        )
    )
    memberships = result.all()
    user_ids = [m.user_id for m in memberships]

    # 3. Get nutrition profiles for all members
    result = await session.exec(
        select(UserNutritionProfile).where(
            UserNutritionProfile.user_id.in_(user_ids)
        )
    )
    profiles = {p.user_id: p for p in result.all()}

    # 4. Extract dish names from meal plan
    dish_names = []
    if meal_plan.breakfast:
        dish_names.extend(meal_plan.breakfast)
    if meal_plan.lunch:
        dish_names.extend(meal_plan.lunch)
    if meal_plan.dinner:
        dish_names.extend(meal_plan.dinner)
    if meal_plan.snacks:
        dish_names.extend(meal_plan.snacks)

    # 5. Try to match dishes to recipe memories
    recipe_memories = {}
    nutrition_info = {}

    if dish_names:
        result = await session.exec(
            select(RecipeMemory)
            .where(RecipeMemory.household_id == current_household.id)
            .where(RecipeMemory.dish_name.in_(dish_names))
        )
        for memory in result.all():
            recipe_memories[memory.dish_name] = memory

            # Get nutrition info for this memory
            nutrition_result = await session.exec(
                select(RecipeNutritionInfo).where(
                    RecipeNutritionInfo.recipe_memory_id == memory.id
                )
            )
            nutrition = nutrition_result.first()
            if nutrition:
                nutrition_info[memory.dish_name] = nutrition

    # 6. Build per-user assessment
    per_user = {}
    issues_count = 0

    for user_id in user_ids:
        profile = profiles.get(user_id)
        if not profile:
            continue

        user_assessment = {}

        # Add goals if set
        if any([
            profile.calories_daily,
            profile.protein_daily_g,
            profile.carbs_daily_g,
            profile.fat_daily_g
        ]):
            user_assessment["goals"] = {}
            if profile.calories_daily:
                user_assessment["goals"]["calories_daily"] = profile.calories_daily
            if profile.protein_daily_g:
                user_assessment["goals"]["protein_daily_g"] = profile.protein_daily_g
            if profile.carbs_daily_g:
                user_assessment["goals"]["carbs_daily_g"] = profile.carbs_daily_g
            if profile.fat_daily_g:
                user_assessment["goals"]["fat_daily_g"] = profile.fat_daily_g

        # Calculate estimated totals from nutrition info
        if nutrition_info:
            est_calories = 0
            est_protein = 0.0
            est_carbs = 0.0
            est_fat = 0.0

            for dish_name in dish_names:
                nutrition = nutrition_info.get(dish_name)
                if nutrition:
                    if nutrition.calories:
                        est_calories += nutrition.calories
                    if nutrition.protein_g:
                        est_protein += nutrition.protein_g
                    if nutrition.carbs_g:
                        est_carbs += nutrition.carbs_g
                    if nutrition.fat_g:
                        est_fat += nutrition.fat_g

            if est_calories > 0 or est_protein > 0:
                user_assessment["est_today"] = {}
                if est_calories > 0:
                    user_assessment["est_today"]["calories"] = est_calories
                if est_protein > 0:
                    user_assessment["est_today"]["protein_g"] = round(est_protein, 1)
                if est_carbs > 0:
                    user_assessment["est_today"]["carbs_g"] = round(est_carbs, 1)
                if est_fat > 0:
                    user_assessment["est_today"]["fat_g"] = round(est_fat, 1)

        # Check for restriction violations
        if profile.restrictions:
            violations = []
            suggestions = []

            for dish_name in dish_names:
                memory = recipe_memories.get(dish_name)
                if not memory:
                    continue

                # Check common restrictions
                if profile.restrictions.get("dairy_free"):
                    # Check if dish has dairy in substitutions or notes
                    dairy_keywords = ["cream", "milk", "cheese", "butter", "yogurt"]
                    dish_lower = dish_name.lower()
                    notes_lower = (memory.origin_notes or "").lower()

                    if any(keyword in dish_lower or keyword in notes_lower for keyword in dairy_keywords):
                        violations.append({
                            "dish": dish_name,
                            "reason": f"May contain dairy (conflicts with dairy_free restriction)"
                        })
                        issues_count += 1

                        # Check if there's a coconut milk substitution available
                        if memory.substitutions and "coconut" in str(memory.substitutions).lower():
                            suggestions.append(
                                f"Use coconut milk substitution for {dish_name}"
                            )
                        else:
                            suggestions.append(
                                f"Consider dairy-free alternative for {dish_name}"
                            )

                if profile.restrictions.get("shellfish_allergy"):
                    shellfish_keywords = ["shrimp", "crab", "lobster", "shellfish", "prawn"]
                    dish_lower = dish_name.lower()

                    if any(keyword in dish_lower for keyword in shellfish_keywords):
                        violations.append({
                            "dish": dish_name,
                            "reason": "Contains shellfish (ALLERGY RISK)"
                        })
                        issues_count += 1
                        suggestions.append(
                            f"⚠️ CRITICAL: Replace {dish_name} - shellfish allergy"
                        )

            if violations:
                user_assessment["restrictions"] = profile.restrictions
                user_assessment["violations"] = violations

            if suggestions:
                user_assessment["suggestions"] = suggestions

        # Add cultural notes if present
        if profile.cultural_notes:
            user_assessment["cultural_notes"] = profile.cultural_notes

        per_user[str(user_id)] = user_assessment

    # 7. Generate summary
    if issues_count == 0:
        summary = "✅ All aligned"
    elif issues_count == 1:
        summary = "⚠️ 1 issue found"
    else:
        summary = f"⚠️ {issues_count} issues found"

    return {
        "date": today.isoformat(),
        "household_id": str(current_household.id),
        "summary": summary,
        "meal_plan": {
            "breakfast": meal_plan.breakfast or [],
            "lunch": meal_plan.lunch or [],
            "dinner": meal_plan.dinner or [],
            "snacks": meal_plan.snacks or []
        },
        "per_user": per_user
    }
