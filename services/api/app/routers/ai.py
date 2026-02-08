from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import get_db
from app.deps import get_workspace
from app.models import Workspace, PantryItem, Recipe, RecipeVariant
from app.services.ai_service import ai_service, SubstitutionSuggestion, RecipeTipsResponse, RecipeDraftResponse
from app.core.ai_client import ai_client
from app.settings import settings as app_settings
from app.infra.redis_client import get_redis
from app.schemas import ChefChatRequest, ChefChatResponse
import json

router = APIRouter(prefix="/ai", tags=["ai"])

# --- Chef Chat (Craft Recipes) ---

@router.post("/chef/chat", response_model=ChefChatResponse)
def chef_chat(
    payload: ChefChatRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """
    Generate or refine a recipe via chat (Gemini).
    Returns a structured draft and assistant text.
    """
    context_data = None
    
    # If refining, fetch context
    if payload.mode == "refine" and payload.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id, Recipe.workspace_id == workspace.id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found for refinement")
            
        # Prioritize specified variant, then active, then migration logic
        variant = None
        if payload.base_variant_id:
             variant = db.query(RecipeVariant).filter(RecipeVariant.id == payload.base_variant_id).first()
        elif recipe.active_variant_id:
             variant = db.query(RecipeVariant).filter(RecipeVariant.id == recipe.active_variant_id).first()
             
        if variant:
            context_data = variant.content_json
        else:
             # Fallback to current recipe state if no variants exist yet (unlikely after migration)
             context_data = {
                 "title": recipe.title,
                 "ingredients": [{"item": i.name, "qty": float(i.qty) if i.qty else None, "unit": i.unit} for i in recipe.ingredients],
                 "steps": [s.title for s in recipe.steps] # simplified
             }

    # Generate
    draft = ai_service.generate_recipe_draft(
        message=payload.message,
        context_recipe=context_data
    )
    
    return ChefChatResponse(
        assistant_message=draft.assistant_message,
        recipe_draft=draft.recipe_json.model_dump(by_alias=True),
        suggested_label=draft.suggested_label,
        source="ai",
        model_id="gemini-flash", # Placeholder, ideally from config
        thread_id=payload.thread_id
    )


@router.get("/status")
def get_ai_status():
    """Debug endpoint for AI availability."""
    images_status = "ready"
    
    if not app_settings.ai_images_enabled:
        images_status = "disabled_by_config"
    elif not app_settings.gemini_api_key:
        images_status = "missing_api_key"
    elif ai_client.image_quota_exceeded:
        images_status = "quota_exceeded"

    images_available = (images_status == "ready")

    return {
        "ai_mode": app_settings.ai_mode,
        "model_text": app_settings.gemini_text_model,
        "images_enabled": app_settings.ai_images_enabled and bool(app_settings.gemini_api_key),
        "images_available": images_available,
        "images_status": images_status,
        "images_reason": images_status, # Keep backwards compatibility for a moment if needed
        "image_provider": "google_genai" if app_settings.ai_images_enabled else "none",
        "image_model": app_settings.ai_image_model if app_settings.ai_images_enabled else None,
        "has_api_key": bool(app_settings.gemini_api_key),
        "last_error": ai_client.last_error,
        "last_error_at": ai_client.last_error_at
    }

class SubstituteRequest(BaseModel):
    ingredient: str
    context: Optional[str] = None

class RecipeTipsRequest(BaseModel):
    recipe_id: str
    scope: str # storage | reheat

@router.post("/recipe_tips", response_model=RecipeTipsResponse)
async def get_recipe_tips(
    payload: RecipeTipsRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get AI-generated tips for storage or reheating (Cached)."""
    # 1. Fetch recipe to ensure existence and getting update time for cache key
    from app.models import Recipe
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 2. Key Construction
    # Use content hash since updated_at is not available/reliable for this model yet
    import hashlib
    ingredients = [i.name for i in recipe.ingredients] if recipe.ingredients else []
    content_sig = f"{recipe.title}|{','.join(sorted(ingredients))}"
    content_hash = hashlib.md5(content_sig.encode()).hexdigest()
    
    cache_key = f"tips:{workspace.id}:{recipe.id}:{payload.scope}:{content_hash}"
    
    # 3. Check Cache
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return RecipeTipsResponse.model_validate_json(cached)
    except Exception as e:
        # Redis fail shouldn't block feature
        pass
        
    # 4. Generate
    # ingredients already extracted above
    
    # Using sync service method (ai_client inside is sync? ai_client.generate_json code is usually sync or async?)
    # ai_service.generate_tips is sync in my implementation above.
    # ideally we should await if network IO.
    # But for now, we run it.
    result = ai_service.generate_tips(
        recipe_title=recipe.title,
        ingredients=ingredients,
        scope=payload.scope
    )
    
    # 5. Cache Result (30 days)
    try:
        if result and redis:
            await redis.set(cache_key, result.model_dump_json(), ex=60*60*24*30)
    except Exception:
        pass
        
    return result

@router.post("/substitute", response_model=SubstitutionSuggestion)
def suggest_substitute(
    payload: SubstituteRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """
    Suggest a substitute for an ingredient based on available pantry items.
    """
    # 1. Fetch pantry items
    stmt = select(PantryItem.name).where(PantryItem.workspace_id == workspace.id)
    pantry_items = db.execute(stmt).scalars().all()
    pantry_list = list(pantry_items)

    # 2. Call AI Service
    suggestion = ai_service.suggest_substitute(
        ingredient=payload.ingredient,
        pantry_items=pantry_list, 
        context=payload.context or ""
    )
    
    return suggestion

class MacroRequest(BaseModel):
    recipe_id: str

@router.post("/macros")
def analyze_macros(
    payload: MacroRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    from app.models import Recipe
    # Fetch recipe
    recipe = db.scalar(select(Recipe).where(Recipe.id == payload.recipe_id))
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ing_names = [i.name for i in recipe.ingredients]
    result = ai_service.summarize_macros(recipe.title, ing_names)
    return result

