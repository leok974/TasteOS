"""Recipes CRUD API router.

Endpoints:
- GET /api/recipes - List recipes in workspace
- POST /api/recipes - Create recipe with steps
- GET /api/recipes/{id} - Get recipe with steps
- PATCH /api/recipes/{id} - Update recipe
"""

import uuid
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, joinedload

from ..core.text import clean_md, parse_step_text, normalize_step_structure

from app.infra.idempotency import idempotency_precheck, idempotency_store_result, idempotency_clear_key

from ..db import get_db
from ..deps import get_workspace
from ..models import Recipe, RecipeStep, RecipeImage, Workspace, RecipeNoteEntry, RecipeIngredient, RecipeVariant
from ..schemas import (
    RecipeCreate, RecipeOut, RecipeListOut, RecipePatch, 
    RecipeNoteEntryOut, RecipeNoteEntryCreate, RecipeLearningsResponse, 
    RecipeVariantCreate, RecipeVariantOut,
    RecipeFromDraftCreate, RecipeVariantFromDraftCreate, SetActiveVariantRequest
)
from ..settings import settings
from ..services.events import log_event
from ..services.storage import storage
from ..services.time_estimate import estimate_recipe_time
from sqlalchemy import desc, select, func, text, or_
from pydantic import BaseModel

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("tasteos.recipes")


def _build_image_url(storage_key: Optional[str], provider: Optional[str] = None) -> Optional[str]:
    """Construct public URL from storage key."""
    if not storage_key:
        return None
    # If key is already a URL or local path, return as is
    if storage_key.startswith("http") or storage_key.startswith("/"):
        return storage_key
        
    # If provider is local-based (google_genai Native uses LocalStorage), use /media
    # TODO: This mapping should be cleaner (e.g. constant)
    if provider == "google_genai":
        return f"/media/{storage_key}"

    return f"{settings.object_public_base_url}/{storage_key}"


def _recipe_to_out(recipe: Recipe) -> RecipeOut:
    """Convert Recipe model to RecipeOut with image URLs."""
    # Build URLs for all images
    for img in recipe.images:
        img.public_url = _build_image_url(img.storage_key, getattr(img, "provider", None))
    
    # Build active image URL explicitly if joined loaded separately
    if recipe.active_image:
        recipe.active_image.public_url = _build_image_url(recipe.active_image.storage_key, getattr(recipe.active_image, "provider", None))

    primary_img = recipe.primary_image
    primary_url = primary_img.public_url if primary_img else None
    
    return RecipeOut(
        id=recipe.id,
        workspace_id=recipe.workspace_id,
        title=recipe.title,
        cuisines=recipe.cuisines,
        tags=recipe.tags,
        servings=recipe.servings,
        time_minutes=recipe.time_minutes,
        notes=recipe.notes,
        steps=recipe.steps,
        ingredients=recipe.ingredients,
        images=recipe.images,
        
        # Versioning
        active_variant_id=recipe.active_variant_id,
        active_variant=recipe.active_variant,
        variants=recipe.variants,
        
        total_minutes=recipe.total_minutes,
        total_minutes_source=recipe.total_minutes_source,
        
        primary_image_url=primary_url,
        created_at=recipe.created_at,
    )


def _recipe_to_list_out(recipe: Recipe) -> RecipeListOut:
    """Convert Recipe model to RecipeListOut for list views."""
    primary_img = recipe.primary_image
    primary_url = None
    
    if primary_img:
         # Use the helper to resolve URL based on provider
         primary_url = _build_image_url(primary_img.storage_key, getattr(primary_img, "provider", None))
         primary_img.public_url = primary_url

    return RecipeListOut(
        id=recipe.id,
        workspace_id=recipe.workspace_id,
        title=recipe.title,
        cuisines=recipe.cuisines,
        tags=recipe.tags,
        servings=recipe.servings,
        time_minutes=recipe.time_minutes,
        total_minutes=recipe.total_minutes,
        total_minutes_source=recipe.total_minutes_source,
        primary_image_url=primary_url,
        created_at=recipe.created_at,
        active_variant_id=recipe.active_variant_id,
        variants=recipe.variants,
    )


@router.get("/recipes", response_model=list[RecipeListOut])
def list_recipes(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """List recipes in the current workspace."""
    query = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.active_image),
            joinedload(Recipe.variants)
        )
        .filter(Recipe.workspace_id == workspace.id)
    )
    
    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(RecipeIngredient).filter(
            or_(
                Recipe.title.ilike(search_pattern),
                RecipeIngredient.name.ilike(search_pattern),
                # Also search tags if available (Json/Array filter depends on DB type, keep simple for now)
            )
        ).distinct() # Reduce because join might multiply rows
    
    recipes = (
        query
        .order_by(Recipe.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [_recipe_to_list_out(r) for r in recipes]


@router.post("/recipes", response_model=RecipeOut, status_code=201)
def create_recipe(
    payload: RecipeCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a new recipe with optional steps."""
    recipe = Recipe(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        title=clean_md(payload.title),
        cuisines=payload.cuisines or [],
        tags=payload.tags or [],
        servings=payload.servings,
        time_minutes=payload.time_minutes,
        notes=payload.notes,
    )
    db.add(recipe)
    
    # Add steps if provided
    steps_list = []
    if payload.steps:
        for step_data in payload.steps:
            step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                step_index=step_data.step_index,
                title=clean_md(step_data.title),
                bullets=[clean_md(b) for b in (step_data.bullets or [])],
                minutes_est=step_data.minutes_est,
            )
            db.add(step)
            
            # Format for variant
            txt = ""
            if step_data.title and not step_data.title.lower().startswith("step"):
                txt += f"**{step_data.title}:** "
            if step_data.bullets:
                txt += " ".join(step_data.bullets)
            elif not txt:
                txt = step_data.title
            steps_list.append(txt)

    # Create Initial "Original" Variant
    content_json = {
        "title": payload.title,
        "yield": {"servings": payload.servings or 4, "unit": "servings"},
        "tags": payload.tags or [],
        "ingredients": [], # No ingredients supported in Create payload yet
        "steps": steps_list,
        "notes": payload.notes
    }

    variant = RecipeVariant(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        label="Original",
        content_json=content_json,
        created_by="user"
    )
    db.add(variant)
    
    # Calculate Cook Time Badge
    query_steps = []
    if payload.steps:
        # Create object-like structs for estimator
        class MockStep:
            def __init__(self, t, b, m):
                self.title = t
                self.bullets = b
                self.minutes_est = m
        for s in payload.steps:
            query_steps.append(MockStep(s.title, s.bullets, s.minutes_est))
            
    # Mock recipe for estimator (no ingredients in CREATE payload)
    class MockRecipe:
        def __init__(self, s):
            self.steps = s
            self.ingredients = []
            
    total_mins, source = estimate_recipe_time(MockRecipe(query_steps))
    recipe.total_minutes = total_mins
    recipe.total_minutes_source = source

    # Set active pointer
    recipe.active_variant_id = variant.active_variant_id = variant.id # Set on object
    
    db.commit()
    db.refresh(recipe)
    
    # Eager load relationships
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.steps), 
            joinedload(Recipe.ingredients),
            joinedload(Recipe.images),
            joinedload(Recipe.active_image),
            joinedload(Recipe.variants),
            joinedload(Recipe.active_variant)
        )
        .filter(Recipe.id == recipe.id)
        .first()
    )
    
    return _recipe_to_out(recipe)


@router.get("/recipes/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get a recipe by ID with all steps and images."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.steps), 
            joinedload(Recipe.ingredients),
            joinedload(Recipe.images),
            joinedload(Recipe.active_image),
            joinedload(Recipe.variants),
            joinedload(Recipe.active_variant)
        )
        .filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
        .first()
    )
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return _recipe_to_out(recipe)


@router.patch("/recipes/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: str,
    payload: RecipePatch,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Update a recipe. If steps are provided, they replace all existing steps."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.steps), 
            joinedload(Recipe.ingredients),
            joinedload(Recipe.images),
            joinedload(Recipe.active_image),
            joinedload(Recipe.variants),
            joinedload(Recipe.active_variant)
        )
        .filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
        .first()
    )
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Update scalar fields
    if payload.title is not None:
        recipe.title = payload.title
    if payload.cuisines is not None:
        recipe.cuisines = payload.cuisines
    if payload.tags is not None:
        recipe.tags = payload.tags
    if payload.servings is not None:
        recipe.servings = payload.servings
    if payload.time_minutes is not None:
        recipe.time_minutes = payload.time_minutes
    if payload.notes is not None:
        recipe.notes = payload.notes
    
    # Replace steps if provided
    if payload.steps is not None:
        # Delete existing steps
        db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe.id).delete()
        
        # Add new steps
        for step_data in payload.steps:
            step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                step_index=step_data.step_index,
                title=step_data.title,
                bullets=step_data.bullets or [],
                minutes_est=step_data.minutes_est,
            )
            db.add(step)
            
    # Re-calculate Cook Time Badge on Update
    # Need to reload current ingredients if steps changed? Or assume ingredients not changed here.
    # Recipe.ingredients is relationship.
    # Need to flush to query relationship correctly unless we rely on session
    db.flush() 
    
    # Reload recipe for accurate estimation
    # Or just use the payload info if complete
    # Easier to do a fresh query or use object if session is consistent.
    # Since we deleted steps via query, session might be out of sync.
    # Safest is to commit or use what we know.
    # Let's commit everything so far, then reload and calc.
    # But we want to save calc in same transaction.
    
    # We load ingredients
    db.refresh(recipe, attribute_names=['ingredients', 'steps'])
    
    total_mins, source = estimate_recipe_time(recipe)
    recipe.total_minutes = total_mins
    recipe.total_minutes_source = source
    
    db.commit()
    db.refresh(recipe)
    
    # Reload with relationships
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.steps), 
            joinedload(Recipe.ingredients),
            joinedload(Recipe.images),
            joinedload(Recipe.active_image)
        )
        .filter(Recipe.id == recipe.id)
        .first()
    )
    
    return _recipe_to_out(recipe)


# --- Image Generation Endpoints ---

# Image generation endpoints moved to routers/images.py


    return {
        "image_id": image.id,
        "status": "pending",
        "message": "Image regeneration started",
    }


# --- Share / Export / Import ---

from ..share_schemas import PortableRecipe, PortableRecipeDetail, PortableIngredient, PortableStep, PortableImageMeta

@router.get("/recipes/{recipe_id}/export", response_model=PortableRecipe)
def export_recipe(
    recipe_id: str,
    download: bool = Query(False),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Export a recipe to portable JSON format."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.steps), 
            joinedload(Recipe.ingredients),
            joinedload(Recipe.active_image),
            joinedload(Recipe.images)
        )
        .filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
        .first()
    )
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build portable ingredients
    p_ingredients = [
        PortableIngredient(
            name=i.name,
            qty=i.qty,
            unit=i.unit,
            category=i.category
        ) for i in recipe.ingredients
    ]

    # Build portable steps
    p_steps = [
        PortableStep(
            step_index=s.step_index,
            title=s.title,
            bullets=s.bullets or [],
            minutes_est=s.minutes_est
        ) for s in sorted(recipe.steps, key=lambda x: x.step_index)
    ]

    # Build portable image meta
    p_image = None
    active_img = recipe.active_image or (recipe.images[0] if recipe.images and recipe.images[0].status == 'ready' else None)
    
    if active_img:
        p_image = PortableImageMeta(
            source=active_img.provider or "uploaded",
            prompt=active_img.prompt
        )

    # Construct portable detail
    detail = PortableRecipeDetail(
        title=recipe.title,
        cuisines=recipe.cuisines or [],
        tags=recipe.tags or [],
        servings=recipe.servings,
        time_minutes=recipe.time_minutes,
        notes=recipe.notes,
        ingredients=p_ingredients,
        steps=p_steps,
        image_meta=p_image
    )

    payload = PortableRecipe(recipe=detail)

    if download:
        from fastapi.responses import JSONResponse
        headers = {
            "Content-Disposition": f'attachment; filename="tasteos-{recipe.id[:8]}.json"'
        }
        return JSONResponse(content=payload.model_dump(mode='json'), headers=headers)
    
    return payload


@router.post("/recipes/import", response_model=dict, status_code=201)
async def import_recipe(
    request: Request,
    payload: PortableRecipe,
    mode: str = Query("dedupe", regex="^(dedupe|copy)$"),
    regen_image: bool = Query(False),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Import a portable recipe into the current workspace."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="recipe_import")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        if payload.schema_version != "tasteos.recipe.v1":
            raise HTTPException(status_code=400, detail=f"Unsupported schema version: {payload.schema_version}")

        pr = payload.recipe
        
        # 1. Dedupe Check
        if mode == "dedupe":
            # Simple fuzzy match on title (case-insensitive)
            existing = (
                db.query(Recipe)
                .filter(
                    Recipe.workspace_id == workspace.id,
                    Recipe.title.ilike(pr.title.strip())
                )
                .first()
            )
            if existing:
                res = {
                    "recipe_id": existing.id,
                    "created": False,
                    "deduped": True,
                    "message": f"Recipe '{existing.title}' already exists."
                }
                await idempotency_store_result(redis_key, req_hash, status=201, body=res)
                return res

        # 2. Create Recipe
        new_recipe = Recipe(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            title=pr.title,
            cuisines=pr.cuisines,
            tags=pr.tags,
            servings=pr.servings,
            time_minutes=pr.time_minutes,
            notes=pr.notes
        )
        db.add(new_recipe)
        
        # 3. Create Ingredients
        from ..models import RecipeIngredient
        for i in pr.ingredients:
            db.add(RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=new_recipe.id,
                name=i.name,
                qty=i.qty,
                unit=i.unit,
                category=i.category
            ))
            
        # 4. Create Steps
        for s in pr.steps:
            db.add(RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=new_recipe.id,
                step_index=s.step_index,
                title=s.title,
                bullets=s.bullets,
                minutes_est=s.minutes_est
            ))

        db.commit()
        db.refresh(new_recipe)

        # 5. Handle Image Regeneration
        if regen_image and settings.ai_enabled:
            # Use existing prompt if available, otherwise construct one
            prompt = pr.image_meta.prompt if (pr.image_meta and pr.image_meta.prompt) else f"Professional food photography of {new_recipe.title}"
            
            image = RecipeImage(
                id=str(uuid.uuid4()),
                recipe_id=new_recipe.id,
                status="pending",
                provider="gemini",
                model=settings.gemini_model,
                prompt=prompt,
            )
            db.add(image)
            db.commit()

        res = {
            "recipe_id": new_recipe.id,
            "created": True,
            "deduped": False,
            "message": "Recipe imported successfully."
        }
        await idempotency_store_result(redis_key, req_hash, status=201, body=res)
        return res
    except Exception:
        await idempotency_clear_key(redis_key)
        raise


@router.get("/recipes/{recipe_id}/share-token", response_model=dict)
def get_share_token(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get a separate compressed token for sharing."""
    # Re-use export logic to get portable structure
    portable = export_recipe(recipe_id, download=False, db=db, workspace=workspace)
    
    from ..parsing import encode_recipe_token
    token = encode_recipe_token(portable.model_dump(mode='json'))
    
    return {"token": token}

# --- Ingestion ---

from pydantic import BaseModel

class IngestRequest(BaseModel):
    text: str
    hints: Optional[dict] = None # e.g. {"servings": 4}
    generate_image: bool = False

@router.post("/recipes/ingest", response_model=RecipeOut, status_code=201)
async def ingest_recipe(
    request: Request,
    payload: IngestRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Ingest a recipe from raw text OR magic token."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="recipe_ingest")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        from ..services.ingestion import IngestionService
        from ..parsing import decode_recipe_token
        
        # Check if text is a token
        if payload.text.strip().startswith("tasteos-v1:"):
            try:
                data = decode_recipe_token(payload.text.strip())
                # Convert dict back to PortableRecipe validation?
                # Ideally we reuse the IMPORT logic now.
                # But IngestService expects text.
                # Let's see... Import endpoint expects PortableRecipe.
                # Maybe we should internally call import_recipe logic?
                # Or make IngestionService capable of handling structured data?
                
                # For MVP simplicity: We will piggyback on the /import logic internally
                # or just map it here.
                
                # Let's map it to PortableRecipe and call the import service logic?
                # We don't have an ImportService, the logic is in the router (bad practice but it is what it is).
                # Let's instigate a quick refactor or just call the router logic? No, calling router from router is messy.
                
                # Better: Let's extract the import logic to a service function eventually.
                # For now, duplicate/inline the creation logic using the decoded data.
                # Actually, the decoded data IS a PortableRecipe structure.
                from ..share_schemas import PortableRecipe
                portable = PortableRecipe(**data)
                
                # Call import_recipe logic (we can refactor import_recipe to use a shared function)
                # Or just redirect? No.
                
                # Let's just use the client to call our own API? No.
                # Let's just create the recipe here using the same logic as import.
                # It's duplication but safier than refactoring everything now.
                
                pr = portable.recipe
                new_recipe = Recipe(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace.id,
                    title=pr.title,
                    cuisines=pr.cuisines,
                    tags=pr.tags,
                    servings=pr.servings,
                    time_minutes=pr.time_minutes,
                    notes=pr.notes
                )
                db.add(new_recipe)
                
                for i in pr.ingredients:
                    from ..models import RecipeIngredient
                    db.add(RecipeIngredient(
                        id=str(uuid.uuid4()),
                        recipe_id=new_recipe.id,
                        name=i.name,
                        qty=i.qty,
                        unit=i.unit,
                        category=i.category
                    ))
                
                for s in pr.steps:
                    db.add(RecipeStep(
                        id=str(uuid.uuid4()),
                        recipe_id=new_recipe.id,
                        step_index=s.step_index,
                        title=s.title,
                        bullets=s.bullets,
                        minutes_est=s.minutes_est
                    ))
                
                db.commit()
                db.refresh(new_recipe)
                recipe = new_recipe
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
                
        else:
            # Normal text ingestion
            service = IngestionService(db)
            recipe = service.ingest_text(workspace.id, payload.text, payload.hints)
        
        # Handle Image Generation if requested
        if payload.generate_image and settings.ai_enabled:
            from ..models import RecipeImage
            image = RecipeImage(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                status="pending",
                provider="gemini",
                model=settings.gemini_model,
                prompt=f"Professional food photography of {recipe.title}",
            )
            db.add(image)
            db.commit()
        
        resp = _recipe_to_out(recipe)
        await idempotency_store_result(redis_key, req_hash, status=201, body=resp.model_dump(mode='json'))
        return resp
    except Exception:
        await idempotency_clear_key(redis_key)
        raise


# --- Recipe Note History Endpoints ---

@router.get("/recipes/{recipe_id}/notes", response_model=list[RecipeNoteEntryOut])
def list_recipe_notes(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
    limit: int = Query(50, ge=1, le=100),
):
    """List note history entries for a recipe, newest first."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    entries = db.query(RecipeNoteEntry).filter(
        RecipeNoteEntry.recipe_id == recipe_id,
        RecipeNoteEntry.workspace_id == workspace.id,
        RecipeNoteEntry.deleted_at.is_(None)
    ).order_by(desc(RecipeNoteEntry.created_at)).limit(limit).all()
    
    return entries


class NotesSearchResponse(BaseModel):
    items: list[RecipeNoteEntryOut]
    next_cursor: Optional[str] = None

@router.get("/recipes/{recipe_id}/notes/search", response_model=NotesSearchResponse)
def search_recipe_notes(
    recipe_id: str,
    q: Optional[str] = None,
    tags: list[str] = Query(default=[]),
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(25, ge=1, le=100),
    cursor: Optional[int] = Query(0, ge=0),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Search and filter recipe notes."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    query = db.query(RecipeNoteEntry).filter(
        RecipeNoteEntry.recipe_id == recipe_id,
        RecipeNoteEntry.workspace_id == workspace.id,
        RecipeNoteEntry.deleted_at.is_(None)
    )
    
    # Text Search (Simple ILIKE for v11)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                RecipeNoteEntry.title.ilike(search_term),
                RecipeNoteEntry.content_md.ilike(search_term)
            )
        )
    
    # Filter by Tags (AND logic)
    if tags:
        query = query.filter(RecipeNoteEntry.tags.contains(tags))
        
    # Filter by Source
    if source:
        query = query.filter(RecipeNoteEntry.source == source)
        
    # Date Range
    if since:
        query = query.filter(RecipeNoteEntry.created_at >= since)
        
    # Pagination & Ordering
    total = query.count()
    items = query.order_by(desc(RecipeNoteEntry.created_at)).offset(cursor).limit(limit).all()
    
    next_cursor = str(cursor + limit) if (cursor + limit) < total else None
    
    return {
        "items": items,
        "next_cursor": next_cursor
    }


class TagCount(BaseModel):
    tag: str
    count: int

class NotesTagsResponse(BaseModel):
    tags: list[TagCount]

@router.get("/recipes/{recipe_id}/notes/tags", response_model=NotesTagsResponse)
def get_recipe_note_tags(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Aggregate tags used in notes for this recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # Postgres specific array aggregation
    # select unnest(tags) as tag, count(*) as count from recipe_note_entries ... group by tag
    stmt = (
        select(func.unnest(RecipeNoteEntry.tags).label("tag"), func.count().label("count"))
        .where(
            RecipeNoteEntry.recipe_id == recipe_id,
            RecipeNoteEntry.workspace_id == workspace.id,
            RecipeNoteEntry.deleted_at.is_(None)
        )
        .group_by("tag")
        .order_by(text("count DESC"))
    )
    
    results = db.execute(stmt).all()
    return {"tags": [{"tag": r.tag, "count": r.count} for r in results]}


@router.post("/recipes/{recipe_id}/notes", response_model=RecipeNoteEntryOut)
async def create_recipe_note(
    recipe_id: str,
    request: Request,
    body: RecipeNoteEntryCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a new note entry, optionally appending to legacy field."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="recipe_create_note")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Duplicate session check
        if body.session_id:
            existing = db.query(RecipeNoteEntry).filter(
                RecipeNoteEntry.recipe_id == recipe_id,
                RecipeNoteEntry.session_id == body.session_id,
                RecipeNoteEntry.deleted_at.is_(None)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Notes for this session already saved (id: {existing.id})"
                )

        entry = RecipeNoteEntry(
            workspace_id=workspace.id,
            recipe_id=recipe_id,
            session_id=body.session_id,
            source=body.source,
            title=body.title,
            content_md=body.content_md,
            applied_to_recipe_notes=body.apply_to_recipe_notes
        )
        db.add(entry)
        
        # Sync legacy field
        if body.apply_to_recipe_notes:
            append_str = f"\n\n---\n{body.title}\n{body.content_md}\n"
            recipe.notes = (recipe.notes or "") + append_str

        log_event(
            db, 
            workspace_id=workspace.id, 
            session_id=body.session_id, 
            type="recipe_note_create", 
            meta={"recipe_id": recipe_id, "note_id": entry.id, "source": body.source}
        )
        
        db.commit()
        db.refresh(entry)
        
        resp = RecipeNoteEntryOut(
            id=entry.id,
            recipe_id=entry.recipe_id,
            title=entry.title,
            content_md=entry.content_md,
            source=entry.source,
            created_at=entry.created_at,
            tags=entry.tags or []
        )
        await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode='json'))
        return resp
    except Exception:
        await idempotency_clear_key(redis_key)
        raisetr = f"\n\n---\n{body.title}\n{body.content_md}\n"
        recipe.notes = (recipe.notes or "") + append_str

    log_event(
        db, 
        workspace_id=workspace.id, 
        session_id=body.session_id, 
        type="recipe_note_create", 
        meta={"recipe_id": recipe_id, "note_id": entry.id, "source": body.source}
    )
    
    db.commit()
    return entry


@router.delete("/recipes/{recipe_id}/notes/{note_id}")
def delete_recipe_note(
    recipe_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Soft-delete a note entry."""
    entry = db.query(RecipeNoteEntry).filter(
        RecipeNoteEntry.id == note_id,
        RecipeNoteEntry.recipe_id == recipe_id,
        RecipeNoteEntry.workspace_id == workspace.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Note entry not found")
        
    from datetime import datetime
    entry.deleted_at = datetime.now()
    
    log_event(
        db, 
        workspace_id=workspace.id, 
        type="recipe_note_delete", 
        meta={"recipe_id": recipe_id, "note_id": note_id}
    )
    db.commit()
    return {"ok": True}


@router.post("/recipes/{recipe_id}/notes/{note_id}/restore", response_model=RecipeNoteEntryOut)
def restore_recipe_note(
    recipe_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Undo delete of a note entry."""
    entry = db.query(RecipeNoteEntry).filter(
        RecipeNoteEntry.id == note_id,
        RecipeNoteEntry.recipe_id == recipe_id,
        RecipeNoteEntry.workspace_id == workspace.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Note entry not found")
        
    entry.deleted_at = None
    
    log_event(
        db, 
        workspace_id=workspace.id, 
        type="recipe_note_restore", 
        meta={"recipe_id": recipe_id, "note_id": note_id}
    )
    db.commit()
    return entry


@router.get("/recipes/{recipe_id}/learnings", response_model=RecipeLearningsResponse)
def get_recipe_learnings(
    recipe_id: str,
    window_days: int = 90,
    limit: int = 5,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get structured learnings and highlights from past cook sessions for this recipe."""
    
    # Check recipe exists
    recipe = db.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Fetch notes
    # Filter by created_at > now - window_days
    cutoff = datetime.now() - timedelta(days=window_days)
    
    notes = db.scalars(
        select(RecipeNoteEntry)
        .where(
            RecipeNoteEntry.recipe_id == recipe_id,
            RecipeNoteEntry.workspace_id == workspace.id,
            # We want cook_recap or manual notes
            RecipeNoteEntry.source.in_(['cook_session', 'manual']),
            RecipeNoteEntry.created_at >= cutoff
        )
        .order_by(desc(RecipeNoteEntry.created_at))
        .limit(20) # Fetch more to analyze
    ).all()
    
    # Analysis Logic
    highlights = []
    tag_counts = {}
    recent_recaps = []
    
    # Common problem keywords
    keywords = {
        "thick": "Texture issue (thick)",
        "thin": "Texture issue (thin)",
        "dry": "Texture issue (dry)",
        "salty": "Flavor issue (salty)",
        "bland": "Flavor issue (bland)",
        "burnt": "Cooking issue (burnt)",
        "raw": "Cooking issue (raw)",
        "time": "Time adjustment",
        "temp": "Temperature adjustment"
    }

    for note in notes:
        # Build recent recaps list (limit to requested return limit)
        if len(recent_recaps) < limit:
            recent_recaps.append({
                "created_at": note.created_at,
                "summary": note.title if note.title != "Cook Recap" else (note.content_md[:50] + "..."),
                "note_entry_id": note.id
            })
            
        # Tally tags
        for tag in note.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        # Extract simple highlights from content
        sentences = note.content_md.split('.')
        for s in sentences:
            s_clean = s.strip()
            if not s_clean: continue
            
            # Check keywords
            found = False
            for k in keywords:
                if k in s_clean.lower():
                    found = True
                    # Also add semantic tag
                    tag_counts[k] = tag_counts.get(k, 0) + 1
            
            if found:
                 if s_clean not in highlights:
                    highlights.append(s_clean)

    # Sort tags by frequency
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    top_tags = [t[0] for t in sorted_tags[:5]]
    
    return RecipeLearningsResponse(
        highlights=highlights[:5], # top 5 highlights
        common_tags=top_tags,
        recent_recaps=recent_recaps
    )

# --- Recipe Macro & Tips Endpoints (v15.3.2) ---

from ..models import RecipeMacroEntry, RecipeTipEntry
from ..schemas import RecipeMacroEntryOut, RecipeMacroEntryCreate, RecipeTipEntryOut, RecipeTipEntryCreate, EstimateMacrosRequest, EstimateTipsRequest
from ..services.ai_service import ai_service
from datetime import datetime

# Helper re-defined just for this block scope if needed, but we can reuse if imports allowed
# But wait, local imports `from ..models` works.

def _get_recipe_for_insights(db: Session, recipe_id: str, workspace_id: str) -> Recipe:
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

@router.get("/recipes/{recipe_id}/macros", response_model=Optional[RecipeMacroEntryOut])
def get_recipe_macros(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get the latest saved macro estimation for a recipe."""
    entry = db.query(RecipeMacroEntry).filter(
        RecipeMacroEntry.recipe_id == recipe_id,
        RecipeMacroEntry.workspace_id == workspace.id
    ).order_by(desc(RecipeMacroEntry.created_at)).first()
    
    return entry


@router.post("/recipes/{recipe_id}/macros", response_model=RecipeMacroEntryOut)
def save_recipe_macros(
    recipe_id: str,
    payload: RecipeMacroEntryCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Save user-defined macro estimation."""
    _get_recipe_for_insights(db, recipe_id, workspace.id)
    
    entry = RecipeMacroEntry(
        workspace_id=workspace.id,
        recipe_id=recipe_id,
        source=payload.source, 
        calories_min=payload.calories_min,
        calories_max=payload.calories_max,
        protein_min=payload.protein_min,
        protein_max=payload.protein_max,
        carbs_min=payload.carbs_min,
        carbs_max=payload.carbs_max,
        fat_min=payload.fat_min,
        fat_max=payload.fat_max,
        confidence=1.0 if payload.source == "user" else None 
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/recipes/{recipe_id}/macros/estimate", response_model=RecipeMacroEntryOut)
def estimate_recipe_macros(
    recipe_id: str,
    request: EstimateMacrosRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Estimate macros using AI or heuristics, optionally persisting."""
    recipe = _get_recipe_for_insights(db, recipe_id, workspace.id)
    
    # Use existing AI service
    ingredients_list = [f"{i.qty or ''} {i.unit or ''} {i.name}" for i in recipe.ingredients]
    result = ai_service.summarize_macros(recipe.title, ingredients_list)
    
    # Map result to model
    calories_min = result.calories_range.get("min")
    calories_max = result.calories_range.get("max")
    protein_min = result.protein_range.get("min") if result.protein_range else None
    protein_max = result.protein_range.get("max") if result.protein_range else None
    
    # Construct entry (even if not persisted, we format it as one)
    # Note: Using current time for transient, but handled by schema
    
    entry_data = {
        "workspace_id": workspace.id,
        "recipe_id": recipe_id,
        "source": result.source,
        "calories_min": calories_min,
        "calories_max": calories_max,
        "protein_min": protein_min,
        "protein_max": protein_max,
        "confidence": 0.9 if result.confidence == "high" else 0.5, 
        "model": "gemini-pro" if result.source == "ai" else "heuristic",
    }
    
    if request.persist:
        entry = RecipeMacroEntry(**entry_data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    else:
        # Return transient object
        return RecipeMacroEntryOut(
            id="transient",
            recipe_id=recipe_id,
            created_at=datetime.utcnow(),
            **entry_data
        )


@router.get("/recipes/{recipe_id}/tips", response_model=Optional[RecipeTipEntryOut])
def get_recipe_tips(
    recipe_id: str,
    scope: str = Query(..., pattern="^(storage|reheat)$"),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get the latest saved tips for a recipe scope."""
    entry = db.query(RecipeTipEntry).filter(
        RecipeTipEntry.recipe_id == recipe_id,
        RecipeTipEntry.workspace_id == workspace.id,
        RecipeTipEntry.scope == scope
    ).order_by(desc(RecipeTipEntry.created_at)).first()
    
    return entry


@router.post("/recipes/{recipe_id}/tips", response_model=RecipeTipEntryOut)
def save_recipe_tips(
    recipe_id: str,
    payload: RecipeTipEntryCreate,
    scope: str = Query(..., pattern="^(storage|reheat)$"),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Save user-defined tips."""
    _get_recipe_for_insights(db, recipe_id, workspace.id)
    
    entry = RecipeTipEntry(
        workspace_id=workspace.id,
        recipe_id=recipe_id,
        scope=scope,
        source=payload.source,
        tips_json=payload.tips_json,
        food_safety_json=payload.food_safety_json,
        confidence=1.0 if payload.source == "user" else None
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --- Variant Management ---

@router.post("/recipes/from-draft", response_model=RecipeOut)
def create_recipe_from_draft(
    payload: RecipeFromDraftCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a new recipe from an AI draft."""
    # PROBE 1: Confirm endpoint reachability
    # raise HTTPException(status_code=418, detail="PROBE: save handler reached") (Completed)
    
    # Sanitize draft content before saving
    if payload.draft.title:
        payload.draft.title = clean_md(payload.draft.title)
    
    # Sanitize and normalize steps
    if payload.draft.steps:
        sanitized_steps = []
        for s in payload.draft.steps:
            if isinstance(s, str):
                sanitized_steps.append(clean_md(s))
            else:
                # Assuming object with title/bullets
                if s.title: s.title = clean_md(s.title)
                if s.bullets: s.bullets = [clean_md(b) for b in s.bullets]
                sanitized_steps.append(s)
        payload.draft.steps = sanitized_steps

    # 1. Create Recipe container
    recipe = Recipe(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        title=payload.draft.title or "Untitled Recipe",
    )
    db.add(recipe)
    db.flush()

    # 1.5. Populate Recipe Steps
    if payload.draft.steps:
        logger.info(f"Saving {len(payload.draft.steps)} steps for recipe {recipe.id}")
        
        # We must update the payload in-place so the Variant content_json is also normalized.
        # Otherwise the Variant stores the "bad" draft while the RecipeStep table gets the "good" data.
        normalized_steps_for_variant = []

        for idx, step_item in enumerate(payload.draft.steps):
            # 1. Access Raw Data
            if isinstance(step_item, str):
                parsed = parse_step_text(step_item) # Legacy fallback
                raw_title = parsed["title"]
                raw_bullets = parsed["bullets"]
                minutes = 5
            else:
                raw_title = step_item.title
                raw_bullets = step_item.bullets
                minutes = step_item.minutes or 5

            # 2. Universal Normalization (Strict)
            normalized = normalize_step_structure(raw_title, raw_bullets)
            
            final_title = normalized["title"]
            final_bullets = normalized["bullets"]

            # HARD GATE: Reject empty bullets
            if not final_bullets:
                logger.error(f"Step {idx+1} rejected due to empty bullets after normalization.")
                raise HTTPException(
                    status_code=422, 
                    detail=f"Step {idx+1} could not be normalized to a valid checklist (empty bullets)."
                )

            # Update the DB Row
            step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                step_index=idx + 1,
                title=final_title,
                bullets=final_bullets,
                minutes_est=minutes,
            )
            db.add(step)

            # Update the Draft Payload for Variant storage
            # We reconstruct the step object (DraftStepIn usually)
            # Since DraftStepIn is a pydantic model, we can just replace the list item?
            # Or simpler: we can't easily replace inside the loop if we don't know the type for sure (str vs dict).
            # But we know `step_item` was from `payload.draft.steps`.
            # Let's perform a direct mutation if it's an object, or replace the list at the end.
            
            # Safe approach: Rebuild the steps list for the payload
            # We need to import DraftStepIn to create new objects, but 'step_item' might be a plain dict if not validated? 
            # No, it's Pydantic model.
            
            # Actually, `payload.draft.steps` is typed `List[Union[DraftStepIn, str]]`.
            # Let's construct a cleaner dict/object representing the normalized state.
            from ..schemas import DraftStepIn # Import inside function to avoid circular if any
            
            normalized_step_obj = DraftStepIn(
                title=final_title,
                bullets=final_bullets,
                minutes=minutes
            )
            normalized_steps_for_variant.append(normalized_step_obj)
        
        # KEY FIX: Replace the payload steps with the normalized ones
        payload.draft.steps = normalized_steps_for_variant

    # 2. Create the first variant
    variant = RecipeVariant(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        recipe_id=recipe.id,
        label=payload.label,
        content_json=payload.draft.model_dump(by_alias=True),
        created_by="ai", 
        model_id=payload.model_id,
        prompt_version=payload.prompt_version
    )
    db.add(variant)
    db.flush()

    # 3. Set as active
    recipe.active_variant_id = variant.id
    db.commit()
    db.refresh(recipe)
    return _recipe_to_out(recipe)


@router.post("/recipes/{recipe_id}/variants/from-draft", response_model=RecipeVariantOut)
def create_variant_from_draft(
    recipe_id: str,
    payload: RecipeVariantFromDraftCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Save an AI draft as a new version of an existing recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # FIX: Normalize the draft payload before saving the variant.
    # Logic mirrors create_recipe_from_draft
    if payload.draft.steps:
        from ..schemas import DraftStepIn
        normalized_steps = []
        
        for idx, step_item in enumerate(payload.draft.steps):
            if isinstance(step_item, str):
                parsed = parse_step_text(step_item)
                raw_title = parsed["title"]
                raw_bullets = parsed["bullets"]
                minutes = 5
            else:
                raw_title = step_item.title
                raw_bullets = step_item.bullets
                minutes = step_item.minutes or 5

            # Universal Normalization
            normalized = normalize_step_structure(raw_title, raw_bullets)
            final_title = normalized["title"]
            final_bullets = normalized["bullets"]

            # Hard Gate
            if not final_bullets:
                raise HTTPException(status_code=422, detail=f"Step {idx+1} invalid (empty bullets)")

            normalized_steps.append(DraftStepIn(
                title=final_title,
                bullets=final_bullets,
                minutes=minutes
            ))
        
        payload.draft.steps = normalized_steps

    variant = RecipeVariant(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        recipe_id=recipe_id,
        label=payload.label,
        content_json=payload.draft.model_dump(by_alias=True),
        created_by="ai",
        model_id=payload.model_id,
        prompt_version=payload.prompt_version
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/recipes/{recipe_id}/variants", response_model=RecipeVariantOut)
def create_variant(
    recipe_id: str,
    payload: RecipeVariantCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a new version (variant) of a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    variant = RecipeVariant(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        recipe_id=recipe_id,
        label=payload.label,
        content_json=payload.content_json,
        created_by="user"
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/recipes/{recipe_id}/active-variant", response_model=RecipeOut)
def set_active_variant(
    recipe_id: str,
    body: Optional[SetActiveVariantRequest] = None,
    # Keep query param for backward compat if needed, but make it optional
    variant_id: Optional[str] = Query(None, description="ID of the variant to set active"),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Switch the active version of a recipe."""
    actual_variant_id = body.variant_id if body else variant_id
    if not actual_variant_id:
        raise HTTPException(status_code=400, detail="variant_id required")

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # Verify variant belongs to recipe
    variant = db.query(RecipeVariant).filter(
        RecipeVariant.id == actual_variant_id, 
        RecipeVariant.recipe_id == recipe_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found for this recipe")
        
    recipe.active_variant_id = actual_variant_id
    db.commit()
    
    # Return updated recipe using get_recipe logic
    return get_recipe(recipe_id, db, workspace)
    return entry


@router.post("/recipes/{recipe_id}/tips/estimate", response_model=RecipeTipEntryOut)
def estimate_recipe_tips(
    recipe_id: str,
    request: EstimateTipsRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Estimate tips using AI, optionally persisting."""
    recipe = _get_recipe_for_insights(db, recipe_id, workspace.id)
    
    ingredients_list = [f"{i.qty or ''} {i.unit or ''} {i.name}" for i in recipe.ingredients]
    result = ai_service.generate_tips(recipe.title, ingredients_list, request.scope)
    
    entry_data = {
        "workspace_id": workspace.id,
        "recipe_id": recipe_id,
        "scope": request.scope,
        "tips_json": result.tips,
        "food_safety_json": result.food_safety,
        "source": result.source,
        "confidence": 0.9 if result.confidence == "high" else 0.5,
        "model": "gemini-pro" if result.source == "ai" else "heuristic",
    }
    
    if request.persist:
        entry = RecipeTipEntry(**entry_data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    else:
        return RecipeTipEntryOut(
            id="transient",
            recipe_id=recipe_id,
            created_at=datetime.utcnow(),
            **entry_data
        )


@router.delete("/recipes/{id}", status_code=204)
def delete_recipe(
    id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Delete a recipe and all its associated data (including images)."""
    recipe = db.query(Recipe).filter(Recipe.id == id, Recipe.workspace_id == workspace.id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 1. Collect image keys to delete from storage
    # We do this before DB delete so we still have the records
    storage_keys_to_delete = []
    
    # Check all associated images
    for image in recipe.images:
        if image.storage_key:
            storage_keys_to_delete.append(image.storage_key)
            
    # 2. Delete from DB
    # The cascade="all, delete-orphan" on relationships handles:
    # - steps
    # - images
    # - ingredients
    # - notes_history
    # - cook_sessions (via FK cascade or manual)
    
    # Optional: manual delete if migration not applied yet
    # from ..models import CookSession
    # db.query(CookSession).filter(CookSession.recipe_id == id).delete()
    
    db.delete(recipe)
    db.commit()

    # 3. Cleanup files from storage (Best effort)
    # We do this after DB commit to ensure DB integrity first.
    # If file deletion fails, it's just orphaned files, which is better than broken DB data.
    for key in storage_keys_to_delete:
        try:
            # Skip if it's an external URL
            if key.startswith("http") or key.startswith("/"):
                continue
            storage.delete(key)
        except Exception as e:
            logger.warning(f"Failed to delete storage key {key} for recipe {id}: {e}")

    return None

