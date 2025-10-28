"""
Nutrition endpoints for TasteOS API.

Provides endpoints to get nutritional information for recipes and variants.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.recipe import Recipe
from tasteos_api.models.variant import RecipeVariant
from tasteos_api.models.recipe_nutrition import RecipeNutrition, RecipeNutritionRead
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
    result = await session.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check ownership
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this recipe")

    # Check for cached nutrition
    nutrition_result = await session.execute(
        select(RecipeNutrition)
        .where(RecipeNutrition.recipe_id == recipe_id)
        .where(RecipeNutrition.variant_id == None)
    )
    cached_nutrition = nutrition_result.scalar_one_or_none()

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
    result = await session.execute(
        select(RecipeVariant).where(RecipeVariant.id == variant_id)
    )
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Get the base recipe to check ownership
    recipe_result = await session.execute(
        select(Recipe).where(Recipe.id == variant.recipe_id)
    )
    recipe = recipe_result.scalar_one_or_none()

    if not recipe or recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this variant")

    # Check for cached nutrition
    nutrition_result = await session.execute(
        select(RecipeNutrition)
        .where(RecipeNutrition.variant_id == variant_id)
    )
    cached_nutrition = nutrition_result.scalar_one_or_none()

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
