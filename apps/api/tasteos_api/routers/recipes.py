"""
Recipes router for recipe management.

This module provides endpoints for creating, reading, updating,
and deleting recipes, as well as recipe search and filtering.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from tasteos_api.core.database import get_db_session
from tasteos_api.core.dependencies import get_current_user
from tasteos_api.models.recipe import Recipe, RecipeCreate, RecipeRead, RecipeUpdate
from tasteos_api.models.user import User

router = APIRouter()


@router.get("/", response_model=list[RecipeRead])
async def list_recipes(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    cuisine: str | None = None,
    difficulty: str | None = None,
) -> list[Recipe]:
    """List all recipes with filtering and pagination."""
    query = select(Recipe).where(
        (Recipe.user_id == current_user.id) | (Recipe.is_public == True)
    )

    if cuisine:
        query = query.where(Recipe.cuisine == cuisine)
    if difficulty:
        query = query.where(Recipe.difficulty == difficulty)

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    recipes = result.scalars().all()

    # Parse JSON fields
    for recipe in recipes:
        recipe.tags = json.loads(recipe.tags) if isinstance(recipe.tags, str) else recipe.tags
        recipe.ingredients = json.loads(recipe.ingredients) if isinstance(recipe.ingredients, str) else recipe.ingredients
        recipe.instructions = json.loads(recipe.instructions) if isinstance(recipe.instructions, str) else recipe.instructions
        recipe.images = json.loads(recipe.images) if isinstance(recipe.images, str) else recipe.images
        if recipe.nutrition:
            recipe.nutrition = json.loads(recipe.nutrition) if isinstance(recipe.nutrition, str) else recipe.nutrition
        if recipe.source:
            recipe.source = json.loads(recipe.source) if isinstance(recipe.source, str) else recipe.source

    return recipes


@router.post("/", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe_data: RecipeCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Recipe:
    """Create a new recipe."""
    # Calculate total time
    total_time = recipe_data.prep_time + recipe_data.cook_time

    # Create recipe with JSON-serialized fields
    db_recipe = Recipe(
        title=recipe_data.title,
        description=recipe_data.description,
        servings=recipe_data.servings,
        prep_time=recipe_data.prep_time,
        cook_time=recipe_data.cook_time,
        total_time=total_time,
        difficulty=recipe_data.difficulty,
        cuisine=recipe_data.cuisine,
        is_public=recipe_data.is_public,
        user_id=current_user.id,
        tags=json.dumps(recipe_data.tags),
        ingredients=json.dumps(recipe_data.ingredients),
        instructions=json.dumps(recipe_data.instructions),
        nutrition=json.dumps(recipe_data.nutrition) if recipe_data.nutrition else None,
        images=json.dumps(recipe_data.images),
        source=json.dumps(recipe_data.source) if recipe_data.source else None,
    )

    session.add(db_recipe)
    await session.commit()
    await session.refresh(db_recipe)

    # Parse JSON fields for response
    db_recipe.tags = recipe_data.tags
    db_recipe.ingredients = recipe_data.ingredients
    db_recipe.instructions = recipe_data.instructions
    db_recipe.nutrition = recipe_data.nutrition
    db_recipe.images = recipe_data.images
    db_recipe.source = recipe_data.source

    return db_recipe


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Recipe:
    """Get a specific recipe by ID."""
    result = await session.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Check access permission
    if recipe.user_id != current_user.id and not recipe.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this recipe"
        )

    # Parse JSON fields
    recipe.tags = json.loads(recipe.tags) if isinstance(recipe.tags, str) else recipe.tags
    recipe.ingredients = json.loads(recipe.ingredients) if isinstance(recipe.ingredients, str) else recipe.ingredients
    recipe.instructions = json.loads(recipe.instructions) if isinstance(recipe.instructions, str) else recipe.instructions
    recipe.images = json.loads(recipe.images) if isinstance(recipe.images, str) else recipe.images
    if recipe.nutrition:
        recipe.nutrition = json.loads(recipe.nutrition) if isinstance(recipe.nutrition, str) else recipe.nutrition
    if recipe.source:
        recipe.source = json.loads(recipe.source) if isinstance(recipe.source, str) else recipe.source

    return recipe


@router.put("/{recipe_id}", response_model=RecipeRead)
async def update_recipe(
    recipe_id: UUID,
    recipe_data: RecipeUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Recipe:
    """Update an existing recipe."""
    result = await session.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Check ownership
    if recipe.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this recipe"
        )

    # Update fields
    update_data = recipe_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ["tags", "ingredients", "instructions"]:
            setattr(recipe, key, json.dumps(value))
        else:
            setattr(recipe, key, value)

    # Recalculate total time if needed
    if "prep_time" in update_data or "cook_time" in update_data:
        recipe.total_time = recipe.prep_time + recipe.cook_time

    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)

    # Parse JSON fields for response
    recipe.tags = json.loads(recipe.tags) if isinstance(recipe.tags, str) else recipe.tags
    recipe.ingredients = json.loads(recipe.ingredients) if isinstance(recipe.ingredients, str) else recipe.ingredients
    recipe.instructions = json.loads(recipe.instructions) if isinstance(recipe.instructions, str) else recipe.instructions
    recipe.images = json.loads(recipe.images) if isinstance(recipe.images, str) else recipe.images
    if recipe.nutrition:
        recipe.nutrition = json.loads(recipe.nutrition) if isinstance(recipe.nutrition, str) else recipe.nutrition
    if recipe.source:
        recipe.source = json.loads(recipe.source) if isinstance(recipe.source, str) else recipe.source

    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a recipe."""
    result = await session.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Check ownership
    if recipe.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this recipe"
        )

    await session.delete(recipe)
    await session.commit()


@router.post("/import")
async def import_recipe(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Import a recipe from URL or text."""
    # TODO: Implement recipe import with AI extraction
    return {
        "message": "Recipe import endpoint - Coming soon!",
        "status": "not_implemented"
    }
