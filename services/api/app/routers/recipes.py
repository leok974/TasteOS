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
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import get_workspace
from ..models import Recipe, RecipeStep, RecipeImage, Workspace, RecipeNoteEntry
from ..schemas import RecipeCreate, RecipeOut, RecipeListOut, RecipePatch, RecipeNoteEntryOut, RecipeNoteEntryCreate
from ..settings import settings
from ..services.events import log_event
from sqlalchemy import desc, select, func, text, or_
from pydantic import BaseModel

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("tasteos.recipes")


def _build_image_url(storage_key: Optional[str]) -> Optional[str]:
    """Construct public URL from storage key."""
    if not storage_key:
        return None
    return f"{settings.object_public_base_url}/{storage_key}"


def _recipe_to_out(recipe: Recipe) -> RecipeOut:
    """Convert Recipe model to RecipeOut with image URLs."""
    # Build URLs for all images
    for img in recipe.images:
        img.public_url = _build_image_url(img.storage_key)
    
    # Build active image URL explicitly if joined loaded separately
    if recipe.active_image:
        recipe.active_image.public_url = _build_image_url(recipe.active_image.storage_key)

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
        primary_image_url=primary_url,
        created_at=recipe.created_at,
    )


def _recipe_to_list_out(recipe: Recipe) -> RecipeListOut:
    """Convert Recipe model to RecipeListOut for list views."""
    # Optimized: property uses active_image if loaded
    if recipe.active_image:
        recipe.active_image.public_url = _build_image_url(recipe.active_image.storage_key)
    
    primary_img = recipe.primary_image
    primary_url = primary_img.public_url if primary_img else _build_image_url(primary_img.storage_key) if primary_img else None
    
    return RecipeListOut(
        id=recipe.id,
        workspace_id=recipe.workspace_id,
        title=recipe.title,
        cuisines=recipe.cuisines,
        tags=recipe.tags,
        servings=recipe.servings,
        time_minutes=recipe.time_minutes,
        primary_image_url=primary_url,
        created_at=recipe.created_at,
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
        .options(joinedload(Recipe.active_image))  # Optimized: only load active
        .filter(Recipe.workspace_id == workspace.id)
    )
    
    if search:
        query = query.filter(Recipe.title.ilike(f"%{search}%"))
    
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
        title=payload.title,
        cuisines=payload.cuisines or [],
        tags=payload.tags or [],
        servings=payload.servings,
        time_minutes=payload.time_minutes,
        notes=payload.notes,
    )
    db.add(recipe)
    
    # Add steps if provided
    if payload.steps:
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
    
    db.commit()
    db.refresh(recipe)
    
    # Eager load relationships
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
            joinedload(Recipe.active_image)
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
            joinedload(Recipe.active_image)
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

@router.post("/recipes/{recipe_id}/image/generate", response_model=dict)
def generate_image(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a pending image generation request.
    
    When AI is enabled, this will enqueue a job to generate the image.
    For now, creates a pending row that can be processed by a worker.
    """
    if not settings.ai_enabled:
        raise HTTPException(
            status_code=503,
            detail="Image generation is disabled. Set AI_ENABLED=1 to enable."
        )
    
    recipe = (
        db.query(Recipe)
        .filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Check if there's already a pending image
    existing_pending = (
        db.query(RecipeImage)
        .filter(RecipeImage.recipe_id == recipe_id, RecipeImage.status == "pending")
        .first()
    )
    if existing_pending:
        return {
            "image_id": existing_pending.id,
            "status": "pending",
            "message": "Image generation already in progress",
        }
    
    # Create new pending image
    image = RecipeImage(
        id=str(uuid.uuid4()),
        recipe_id=recipe_id,
        status="pending",
        provider="gemini",
        model=settings.gemini_model,
        prompt=f"Professional food photography of {recipe.title}",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    
    # TODO: Enqueue job to worker (Redis + RQ)
    # For now, the worker can poll for pending images
    
    return {
        "image_id": image.id,
        "status": "pending",
        "message": "Image generation started",
    }


@router.get("/recipes/{recipe_id}/image", response_model=dict)
def get_image_status(
    recipe_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get the current image status for a recipe."""
    recipe = (
        db.query(Recipe)
        .filter(Recipe.id == recipe_id, Recipe.workspace_id == workspace.id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Get most recent image (ready preferred, then pending, then failed)
    image = (
        db.query(RecipeImage)
        .filter(RecipeImage.recipe_id == recipe_id)
        .order_by(
            # Prioritize: ready > pending > failed
            (RecipeImage.status == "ready").desc(),
            (RecipeImage.status == "pending").desc(),
            RecipeImage.created_at.desc(),
        )
        .first()
    )
    
    if not image:
        return {
            "image_id": None,
            "status": "none",
            "public_url": None,
            "provider": None,
            "model": None,
            "prompt": None,
        }
    
    return {
        "image_id": image.id,
        "status": image.status,
        "public_url": _build_image_url(image.storage_key) if image.status == "ready" else None,
        "provider": image.provider,
        "model": image.model,
        "prompt": image.prompt,
    }


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
def import_recipe(
    payload: PortableRecipe,
    mode: str = Query("dedupe", regex="^(dedupe|copy)$"),
    regen_image: bool = Query(False),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Import a portable recipe into the current workspace."""
    
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
            return {
                "recipe_id": existing.id,
                "created": False,
                "deduped": True,
                "message": f"Recipe '{existing.title}' already exists."
            }

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

    return {
        "recipe_id": new_recipe.id,
        "created": True,
        "deduped": False,
        "message": "Recipe imported successfully."

    }


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
def ingest_recipe(
    payload: IngestRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Ingest a recipe from raw text OR magic token."""
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
    
    return _recipe_to_out(recipe)


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
def create_recipe_note(
    recipe_id: str,
    body: RecipeNoteEntryCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create a new note entry, optionally appending to legacy field."""
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
