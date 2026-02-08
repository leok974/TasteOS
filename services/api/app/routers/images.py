import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models import Recipe, RecipeImage, Workspace
from ..core.ai_client import ai_client
from ..services.storage import storage
from ..settings import settings
from ..deps import get_workspace

logger = logging.getLogger("tasteos.images")

router = APIRouter()

class GenerateImageRequest(BaseModel):
    purpose: str = "card" # card, hero
    style: str = "photo" # photo, illustration

class GenerateImageResponse(BaseModel):
    image_id: str
    image_url: str
    purpose: str
    provider: str
    model: str
    is_ai: bool

@router.post("/recipes/{recipe_id}/images/generate", response_model=GenerateImageResponse)
def generate_recipe_image(
    recipe_id: str,
    payload: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """
    Generate an AI image for a recipe.
    """
    # 1. Guardrails
    if not settings.ai_images_enabled:
         raise HTTPException(status_code=409, detail={"error": "image_generation_disabled"})
    
    if not ai_client.is_available():
         raise HTTPException(status_code=409, detail={"error": "missing_ai_key"})

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 2. Prompt Construction
    prompt = f"High-quality food photo of {recipe.title}, studio lighting, shallow depth of field, appetizing, 4k"
    if payload.style == "illustration":
        prompt = f"Artistic illustration of {recipe.title}, food art, vibrant colors"
    
    # 3. Call AI (Synchronous for now to return result immediately, or Async if slow?)
    # Image gen can take 5-10s. The prompt implies we return the result.
    # Frontend shows spinner.
    
    try:
        # Use a model from settings
        model = settings.ai_image_model
        
        images_bytes = ai_client.generate_image(prompt=prompt, model=model)
        
        if not images_bytes or not images_bytes[0]:
            raise HTTPException(status_code=500, detail="AI returned no image")

        image_data = images_bytes[0]
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        # Pass 429 explicitly if it's a quota issue
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            raise HTTPException(status_code=429, detail="AI Usage Quota Exceeded. Please try again later.")
        
        raise HTTPException(status_code=422, detail=f"Generation failed: {str(e)}")

    # 4. Storage
    image_id = str(uuid.uuid4())
    storage_key = f"recipes/{recipe_id}/images/{image_id}.jpg"
    
    try:
        public_url = storage.put_bytes(storage_key, image_data, content_type="image/jpeg")
    except Exception as e:
        logger.error(f"Storage failed: {e}")
        raise HTTPException(status_code=500, detail="Storage failed")

    # 5. DB Metadata
    db_image = RecipeImage(
        id=image_id,
        recipe_id=recipe_id,
        status="ready",
        storage_key=storage_key,
        provider="google_genai",
        model=model,
        prompt=prompt,
        width=1024, # Assumption for Imagen
        height=1024
    )
    db.add(db_image)
    
    # Force insert of image first to satisfy FK constraint from Recipe -> RecipeImage
    db.flush()
    
    # Update active image if none exists or force update? 
    # Let's set it as active.
    recipe.active_image_id = image_id
    db.add(recipe)
    
    db.commit()
    db.refresh(db_image)
    
    return GenerateImageResponse(
        image_id=image_id,
        image_url=public_url,
        purpose=payload.purpose,
        provider="google_genai",
        model=model,
        is_ai=True
    )

@router.get("/recipes/{recipe_id}/image", response_model=dict)
def get_image_status(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get the current image status for a recipe (Legacy/Poller)."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    image = recipe.primary_image
    
    if not image:
        # Fallback check
        from sqlalchemy import desc
        image = (
            db.query(RecipeImage)
            .filter(RecipeImage.recipe_id == recipe_id)
            .order_by(desc(RecipeImage.created_at))
            .first()
        )

    if not image:
        return {"status": "none", "public_url": None}

    # Helper for public URL construction
    url = None
    if image.storage_key:
        if image.storage_key.startswith("http") or image.storage_key.startswith("/"):
            url = image.storage_key
        else:
             url = f"/media/{image.storage_key}"

    return {
        "image_id": image.id,
        "status": image.status,
        "public_url": url,
        "provider": image.provider,
        "model": image.model
    }
