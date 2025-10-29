"""
Variants router for recipe variant generation.

This module provides endpoints for generating and managing
AI-powered recipe variants using LangGraph.
"""

from typing import Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.agents import VariantGeneratorAgent
from tasteos_api.core.database import get_db_session
from tasteos_api.core.dependencies import get_current_user
from tasteos_api.core.quotas import check_variant_quota, record_variant_usage
from tasteos_api.models.recipe import Recipe
from tasteos_api.models.user import User
from tasteos_api.models.variant import RecipeVariant, VariantCreate, VariantRead

router = APIRouter()

# Initialize the variant generator agent
variant_agent = VariantGeneratorAgent()


@router.post("/generate", response_model=VariantRead)
async def generate_variant(
    recipe_id: UUID,
    variant_type: str,
    dietary_restriction: Optional[str] = None,
    target_cuisine: Optional[str] = None,
    substitutions: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> RecipeVariant:
    """Generate a new recipe variant using AI."""

    # Check daily quota
    quota_status = await check_variant_quota(current_user, session)
    if not quota_status["allowed"]:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Daily variant generation limit reached. Please upgrade to continue.",
                "plan": quota_status["plan"],
                "used": quota_status["used"],
                "limit": quota_status["limit"]
            }
        )

    # Fetch the original recipe
    result = await session.exec(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.first()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check if user owns the recipe or if it's public
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create variants of this recipe")

    # Build preferences from parameters
    preferences = {}
    if dietary_restriction:
        preferences["dietary_restriction"] = dietary_restriction
    if target_cuisine:
        preferences["target_cuisine"] = target_cuisine
    if substitutions:
        preferences["substitutions"] = substitutions

    # Convert recipe to dict for agent
    recipe_dict = {
        "title": recipe.title,
        "description": recipe.description,
        "servings": recipe.servings,
        "prep_time": recipe.prep_time,
        "cook_time": recipe.cook_time,
        "difficulty": recipe.difficulty,
        "cuisine": recipe.cuisine,
        "tags": recipe.tags,
        "ingredients": recipe.ingredients,
        "instructions": recipe.instructions
    }

    # Generate variant using LangGraph agent
    result = await variant_agent.generate_variant(
        recipe_id=recipe_id,
        recipe=recipe_dict,
        variant_type=variant_type,
        preferences=preferences
    )

    # Create variant in database
    generated_variant = result["variant"]
    variant_data = VariantCreate(
        parent_recipe_id=recipe_id,
        title=generated_variant.get("title", f"{recipe.title} - {variant_type}"),
        description=generated_variant.get("description", f"{variant_type.title()} variant"),
        variant_type=variant_type,
        status="generated",
        changes=result["changes"],
        generation_metadata=result["metadata"]
    )

    db_variant = RecipeVariant(
        **variant_data.model_dump(),
        user_id=current_user.id,
        confidence_score=result["confidence_score"]
    )

    session.add(db_variant)
    await session.commit()
    await session.refresh(db_variant)

    # Record usage for quota tracking
    await record_variant_usage(current_user.id, recipe_id, variant_type, session)

    return db_variant


@router.get("/{variant_id}", response_model=VariantRead)
async def get_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> RecipeVariant:
    """Get a specific recipe variant."""
    result = await session.exec(
        select(RecipeVariant).where(RecipeVariant.id == variant_id)
    )
    variant = result.first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return variant


@router.get("/recipe/{recipe_id}", response_model=list[VariantRead])
async def list_recipe_variants(
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> list[RecipeVariant]:
    """List all variants for a specific recipe."""
    recipe_result = await session.exec(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = recipe_result.first()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.exec(
        select(RecipeVariant).where(RecipeVariant.parent_recipe_id == recipe_id)
    )
    variants = result.all()

    return list(variants)


@router.post("/{variant_id}/approve", response_model=VariantRead)
async def approve_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> RecipeVariant:
    """Approve a generated variant."""
    result = await session.exec(
        select(RecipeVariant).where(RecipeVariant.id == variant_id)
    )
    variant = result.first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    variant.status = "approved"
    session.add(variant)
    await session.commit()
    await session.refresh(variant)

    return variant


@router.get("/{variant_id}/diff")
async def get_variant_diff(
    variant_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Get the diff between original recipe and variant."""
    variant_result = await session.exec(
        select(RecipeVariant).where(RecipeVariant.id == variant_id)
    )
    variant = variant_result.first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    recipe_result = await session.exec(
        select(Recipe).where(Recipe.id == variant.parent_recipe_id)
    )
    recipe = recipe_result.first()

    if not recipe:
        raise HTTPException(status_code=404, detail="Original recipe not found")

    return {
        "variant_id": str(variant.id),
        "recipe_id": str(recipe.id),
        "changes": variant.changes,
        "variant_type": variant.variant_type,
        "original": {
            "title": recipe.title,
            "description": recipe.description,
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions
        },
        "modified": {
            "title": variant.title,
            "description": variant.description
        },
        "confidence_score": variant.confidence_score
    }
