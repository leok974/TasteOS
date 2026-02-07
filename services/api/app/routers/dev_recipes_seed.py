from typing import List, Optional
import hashlib
import logging
import uuid
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models import Recipe, Workspace
from ..deps import get_workspace_optional
# Removed unused imports that caused errors (import_recipe does not exist)

router = APIRouter()
logger = logging.getLogger("tasteos.dev")

class RecipeSeedItem(BaseModel):
    title_hint: str
    text: str

class RecipeSeedRequest(BaseModel):
    workspace_id: Optional[str] = None
    mode: str = "ingest"
    recipes: List[RecipeSeedItem]

class RecipeSeedResult(BaseModel):
    recipe_id: Optional[str] = None
    title: str
    steps: int
    ingredients: int
    ignored: bool = False
    error: Optional[str] = None

class RecipeSeedResponse(BaseModel):
    created: List[RecipeSeedResult]
    failed: List[dict]
    ignored: List[RecipeSeedResult]

def compute_hash(text: str) -> str:
    """Compute normalized hash of recipe text."""
    normalized = text.strip().lower().replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

@router.post("/dev/recipes/seed", response_model=RecipeSeedResponse)
async def seed_recipes_batch(
    body: RecipeSeedRequest,
    db: Session = Depends(get_db),
    workspace_opt: Optional[Workspace] = Depends(get_workspace_optional),
):
    """Seed recipes from plain text with idempotency."""
    
    # 1. Resolve Workspace
    workspace_id = body.workspace_id
    if not workspace_id and workspace_opt:
        workspace_id = workspace_opt.id
    
    if not workspace_id:
        # Find ANY workspace to default to (Dev helper behavior)
        # Check if workspace_opt is None means no header provided, try finding first one
        ws = db.query(Workspace).first()
        if ws:
            workspace_id = ws.id
        else:
            raise HTTPException(status_code=400, detail="No workspace found or provided")

    workspace = db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    created_results = []
    failed_results = []
    ignored_results = []

    for item in body.recipes:
        logger.info(f"Seeding recipe: {item.title_hint}")
        
        # 2. Idempotency Check
        text_hash = compute_hash(item.text)
        existing = db.scalar(
            select(Recipe).where(
                Recipe.workspace_id == workspace_id,
                Recipe.source_hash == text_hash
            )
        )
        
        if existing:
            ignored_results.append(RecipeSeedResult(
                recipe_id=existing.id,
                title=existing.title,
                steps=len(existing.steps),
                ingredients=len(existing.ingredients),
                ignored=True
            ))
            continue

        try:
            # 3. Call Ingestion Logic
            from ..services.ingestion import IngestionService
            
            # Instantiate service with current DB session
            service = IngestionService(db)
            
            # Using the synchronous `ingest_text` method which uses rule-based parser.
            # If we wanted AI, we'd need a different service or method.
            # For "Seed", we want robust AI parsing?
            # The user asked: "call your existing POST /api/recipes/ingest internally (same code path)"
            # Let's check what /api/recipes/ingest does.
            # It seems it does NOT use IngestionService directly in the file I read previously (routers/recipes.py)
            # wait, routers/recipes.py imported IngestionService inside the function. 
            # But the file content of ingestion.py shows `RuleBasedParser`.
            # If the user wants AI ingestion, we probably need `AiIngestionService` or similar.
            # Let's assume IngestionService is the correct one for now, or check for AI service.
            
            # Actually, `IngestionService` in `ingestion.py` uses `RuleBasedParser`. This might be too weak for "Paste recipes".
            # The user likely has an AI parser somewhere if they want to paste "plain text".
            # Let's check `services/api/app/parsing/__init__.py` or similar.
            
            # Re-reading routers/recipes.py... it imports `from ..services.ingestion import IngestionService`
            # If `IngestionService` is purely rule-based, then "ingest" endpoint is rule-based.
            # But the prompt says "drop in ChatGPT recipes fast". Rule based might be brittle.
            # But the user said "call your existing ... internally". So I should use whatever is existing.
            
            new_recipe = service.ingest_text(
                workspace_id=workspace_id,
                text=item.text,
                hints={"title_hint": item.title_hint}
            )
            
            # Patch the source_hash manually since service doesn't know about it
            new_recipe.source_hash = text_hash
            db.add(new_recipe)
            db.commit() # Save the hash
            
            created_results.append(RecipeSeedResult(
                recipe_id=new_recipe.id,
                title=new_recipe.title,
                steps=len(new_recipe.steps) if new_recipe.steps else 0,
                ingredients=len(new_recipe.ingredients) if new_recipe.ingredients else 0
            ))

        except Exception as e:
            logger.error(f"Failed to seed recipe {item.title_hint}: {e}")
            failed_results.append({
                "title_hint": item.title_hint,
                "error": str(e)
            })
            db.rollback() 

    return RecipeSeedResponse(
        created=created_results,
        failed=failed_results,
        ignored=ignored_results
    )
