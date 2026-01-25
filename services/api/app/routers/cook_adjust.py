"""Cook session adjustment endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging
from typing import List

from ..db import get_db
from ..deps import get_workspace
from ..models import Workspace, CookSession, Recipe
from ..schemas import (
    AdjustPreviewRequest, AdjustPreviewResponse,
    AdjustApplyRequest, SessionResponse
)
from ..services.cook_adjustments import generate_adjustment
from .cook import notify_session_update, session_to_response

router = APIRouter(prefix="/cook", tags=["cook-adjust"])
logger = logging.getLogger("tasteos.cook.adjust")

@router.post("/session/{session_id}/adjust/preview", response_model=AdjustPreviewResponse)
def preview_adjustment(
    session_id: str,
    request: AdjustPreviewRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Preview a step adjustment."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Get current steps
    # If session.steps_override exists, use it. Else fetch recipe steps.
    current_steps = []
    if session.steps_override:
        current_steps = session.steps_override
    else:
        # Fetch from recipe
        recipe = db.scalar(
            select(Recipe).where(Recipe.id == session.recipe_id)
        )
        if not recipe:
             raise HTTPException(status_code=404, detail="Recipe not found")
        # Convert ORM steps to dicts
        current_steps = [
            {
                "step_index": s.step_index,
                "title": s.title,
                "bullets": s.bullets,
                "minutes_est": s.minutes_est
            }
            for s in sorted(recipe.steps, key=lambda x: x.step_index)
        ]

    # Find target step
    original_step = None
    target_idx = -1
    for i, s in enumerate(current_steps):
        if s["step_index"] == request.step_index:
            original_step = s
            target_idx = i
            break
            
    if not original_step:
        # Fallback if step_index is out of range but we have steps?
        # Actually, recipe might have changed, or method switch.
        # Try finding by index position if step_index is just 0-based index?
        # RecipeStep.step_index is reliable.
        raise HTTPException(status_code=404, detail=f"Step {request.step_index} not found")

    # Generate Adjustment
    adjustment = generate_adjustment(
        session_method_key=session.method_key,
        step_index=request.step_index,
        original_step=original_step,
        kind=request.kind,
        context=request.context
    )

    # Create preview steps (copy)
    steps_preview = [s.copy() for s in current_steps]
    
    # Modify the target step
    new_step = steps_preview[target_idx].copy()
    new_step["title"] = adjustment.title
    new_step["bullets"] = adjustment.bullets
    
    if adjustment.warnings:
         new_step["bullets"] = new_step["bullets"] + [f"⚠️ {w}" for w in adjustment.warnings]

    steps_preview[target_idx] = new_step

    return AdjustPreviewResponse(
        adjustment=adjustment,
        steps_preview=steps_preview,
        diff={
            "step_index": request.step_index,
            "changed_fields": ["title", "bullets"],
            "before": {
                "title": original_step.get("title", ""),
                "bullets": original_step.get("bullets", [])
            },
            "after": {
                "title": new_step["title"],
                "bullets": new_step["bullets"]
            }
        }
    )

@router.post("/session/{session_id}/adjust/apply", response_model=SessionResponse)
def apply_adjustment(
    session_id: str,
    request: AdjustApplyRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Apply an adjustment to the session."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Update session
    session.steps_override = request.steps_override
    
    # Append to log
    # adjustments_log is a JSONB list of dicts
    current_log = list(session.adjustments_log) if session.adjustments_log else []
    
    entry = request.adjustment.model_dump(mode='json')
    entry["applied_at"] = str(datetime.utcnow())
    current_log.append(entry)
    
    session.adjustments_log = current_log
    session.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    notify_session_update(session)
    return session_to_response(session)
