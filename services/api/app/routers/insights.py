import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..deps import get_workspace
from ..models import Workspace, NoteInsightsCache
from ..schemas import InsightsRequest, InsightsResponse
from ..insights.notes_facts import NotesFactsBuilder
from ..insights.generator import InsightsGenerator

router = APIRouter()
logger = logging.getLogger("tasteos.insights")

@router.post("/insights/notes", response_model=InsightsResponse)
async def get_notes_insights(
    body: InsightsRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """
    Generate or retrieve cached insights based on note history.
    """
    
    # 1. Build Facts
    builder = NotesFactsBuilder(db, str(workspace.id))
    facts = builder.build_facts(
        recipe_id=body.recipe_id,
        window_days=body.window_days
    )
    
    # 2. Compute Hash
    facts_hash = builder.hash_facts(facts)
    
    # 3. Check Cache
    if not body.force:
        cached = db.query(NoteInsightsCache).filter(
            NoteInsightsCache.workspace_id == str(workspace.id),
            NoteInsightsCache.scope == body.scope,
            NoteInsightsCache.recipe_id == (str(body.recipe_id) if body.scope == "recipe" and body.recipe_id else None),
            NoteInsightsCache.facts_hash == facts_hash,
            NoteInsightsCache.window_days == body.window_days,
            NoteInsightsCache.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if cached:
            logger.info("Serving insights from cache")
            # Parse stored JSON into Pydantic model
            return InsightsResponse(**cached.result_json)

    # 4. Generate with AI (or Fallback)
    generator = InsightsGenerator()
    result = await generator.generate_with_ai(facts, body.style)
    
    if not result:
        logger.info("AI generation failed or disabled, using heuristic fallback")
        result = generator.generate_heuristic_fallback(facts)
    
    # 5. Save to Cache
    # Remove old entry for this scope/params to keep table clean? 
    # Or just let them expire. For now, strict 'latest' replacement might be better.
    
    # Delete match if exists (even if expired, or if we forced refresh)
    db.query(NoteInsightsCache).filter(
         NoteInsightsCache.workspace_id == str(workspace.id),
         NoteInsightsCache.scope == body.scope,
         NoteInsightsCache.recipe_id == (str(body.recipe_id) if body.scope == "recipe" and body.recipe_id else None),
         NoteInsightsCache.window_days == body.window_days,
    ).delete()
    
    new_cache = NoteInsightsCache(
        workspace_id=str(workspace.id),
        scope=body.scope,
        recipe_id=str(body.recipe_id) if body.recipe_id else None,
        window_days=body.window_days,
        facts_hash=facts_hash,
        model=result.model,
        result_json=result.model_dump(mode='json'),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(new_cache)
    db.commit()
    
    return result
