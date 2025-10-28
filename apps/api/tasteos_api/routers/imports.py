"""
Recipe import endpoints for TasteOS API.

Provides endpoints to import recipes from URLs and images.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, HttpUrl
from sqlmodel.ext.asyncio.session import AsyncSession

from tasteos_api.core.dependencies import get_current_user
from tasteos_api.core.database import get_db_session
from tasteos_api.models.user import User
from tasteos_api.models.recipe import Recipe, RecipeCreate, RecipeRead
from tasteos_api.agents import recipe_importer


router = APIRouter(prefix="/imports", tags=["imports"])


class ImportUrlRequest(BaseModel):
    """Request body for URL import."""
    url: HttpUrl


class ImportUrlResponse(BaseModel):
    """Response for successful import."""
    recipe: RecipeRead
    message: str = "Recipe imported successfully"


@router.post("/url", response_model=ImportUrlResponse)
async def import_from_url(
    request: ImportUrlRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ImportUrlResponse:
    """
    Import a recipe from a URL.

    This endpoint:
    - Fetches the recipe page
    - Extracts structured recipe data
    - Creates a new recipe in the database
    - Returns the created recipe

    Args:
        request: Contains the URL to import from
        current_user: Authenticated user
        session: Database session

    Returns:
        The newly created recipe

    Raises:
        HTTPException: If import fails
    """
    try:
        # Import recipe data from URL
        recipe_data = await recipe_importer.import_from_url(str(request.url))

        # Create RecipeCreate model
        recipe_create = RecipeCreate(**recipe_data)

        # Calculate total_time
        total_time = recipe_create.prep_time + recipe_create.cook_time

        # Create Recipe database model
        db_recipe = Recipe(
            title=recipe_create.title,
            description=recipe_create.description,
            servings=recipe_create.servings,
            prep_time=recipe_create.prep_time,
            cook_time=recipe_create.cook_time,
            total_time=total_time,
            difficulty=recipe_create.difficulty,
            cuisine=recipe_create.cuisine,
            is_public=False,
            user_id=current_user.id,
            tags=json.dumps(recipe_create.tags),
            ingredients=json.dumps(recipe_create.ingredients),
            instructions=json.dumps(recipe_create.instructions),
            nutrition=json.dumps(recipe_create.nutrition) if recipe_create.nutrition else None,
            images=json.dumps(recipe_create.images),
            source=json.dumps(recipe_create.source) if recipe_create.source else None,
        )

        session.add(db_recipe)
        await session.commit()
        await session.refresh(db_recipe)

        # Convert to RecipeRead for response
        recipe_read = RecipeRead(
            id=db_recipe.id,
            user_id=db_recipe.user_id,
            title=db_recipe.title,
            description=db_recipe.description,
            servings=db_recipe.servings,
            prep_time=db_recipe.prep_time,
            cook_time=db_recipe.cook_time,
            total_time=db_recipe.total_time,
            difficulty=db_recipe.difficulty,
            cuisine=db_recipe.cuisine,
            is_public=db_recipe.is_public,
            tags=json.loads(db_recipe.tags),
            ingredients=json.loads(db_recipe.ingredients),
            instructions=json.loads(db_recipe.instructions),
            nutrition=json.loads(db_recipe.nutrition) if db_recipe.nutrition else None,
            images=json.loads(db_recipe.images),
            source=json.loads(db_recipe.source) if db_recipe.source else None,
            rating=db_recipe.rating,
            created_at=db_recipe.created_at,
            updated_at=db_recipe.updated_at,
        )

        return ImportUrlResponse(recipe=recipe_read)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import recipe from URL: {str(e)}"
        )


@router.post("/image", response_model=ImportUrlResponse)
async def import_from_image(
    image: Annotated[UploadFile, File(description="Recipe image to import")],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ImportUrlResponse:
    """
    Import a recipe from an image.

    This endpoint:
    - Receives an uploaded image
    - Extracts text via OCR
    - Uses LLM to structure the recipe
    - Creates a new recipe in the database

    Args:
        image: Uploaded image file
        current_user: Authenticated user
        session: Database session

    Returns:
        The newly created recipe

    Raises:
        HTTPException: If import fails or file type is invalid
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, etc.)"
        )

    try:
        # Read image bytes
        image_bytes = await image.read()

        # Import recipe data from image
        recipe_data = await recipe_importer.import_from_image(
            image_bytes,
            filename=image.filename or "recipe.jpg"
        )

        # Create RecipeCreate model
        recipe_create = RecipeCreate(**recipe_data)

        # Calculate total_time
        total_time = recipe_create.prep_time + recipe_create.cook_time

        # Create Recipe database model
        db_recipe = Recipe(
            title=recipe_create.title,
            description=recipe_create.description,
            servings=recipe_create.servings,
            prep_time=recipe_create.prep_time,
            cook_time=recipe_create.cook_time,
            total_time=total_time,
            difficulty=recipe_create.difficulty,
            cuisine=recipe_create.cuisine,
            is_public=False,
            user_id=current_user.id,
            tags=json.dumps(recipe_create.tags),
            ingredients=json.dumps(recipe_create.ingredients),
            instructions=json.dumps(recipe_create.instructions),
            nutrition=json.dumps(recipe_create.nutrition) if recipe_create.nutrition else None,
            images=json.dumps(recipe_create.images),
            source=json.dumps({"type": "image_upload", "filename": image.filename}),
        )

        session.add(db_recipe)
        await session.commit()
        await session.refresh(db_recipe)

        # Convert to RecipeRead for response
        recipe_read = RecipeRead(
            id=db_recipe.id,
            user_id=db_recipe.user_id,
            title=db_recipe.title,
            description=db_recipe.description,
            servings=db_recipe.servings,
            prep_time=db_recipe.prep_time,
            cook_time=db_recipe.cook_time,
            total_time=db_recipe.total_time,
            difficulty=db_recipe.difficulty,
            cuisine=db_recipe.cuisine,
            is_public=db_recipe.is_public,
            tags=json.loads(db_recipe.tags),
            ingredients=json.loads(db_recipe.ingredients),
            instructions=json.loads(db_recipe.instructions),
            nutrition=json.loads(db_recipe.nutrition) if db_recipe.nutrition else None,
            images=json.loads(db_recipe.images),
            source=json.loads(db_recipe.source) if db_recipe.source else None,
            rating=db_recipe.rating,
            created_at=db_recipe.created_at,
            updated_at=db_recipe.updated_at,
        )

        return ImportUrlResponse(
            recipe=recipe_read,
            message="Recipe imported from image successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import recipe from image: {str(e)}"
        )
