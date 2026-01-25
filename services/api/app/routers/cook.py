"""Cook session API router for Cook Assist v1.

Endpoints:
- POST /session/start - Create or return active session
- GET /session/active - Get active session for recipe
- PATCH /session/{id} - Update session state
- POST /assist - AI-powered cooking assistance
"""

import uuid
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from ..db import get_db
from ..deps import get_workspace
from ..models import Workspace, CookSession, Recipe
from ..services.ai_service import ai_service

router = APIRouter(prefix="/cook", tags=["cook"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("tasteos.cook")


# --- Request/Response Models ---

class SessionStartRequest(BaseModel):
    recipe_id: str

class SessionResponse(BaseModel):
    id: str
    recipe_id: str
    status: str
    started_at: str
    current_step_index: int
    step_checks: dict
    timers: dict

class StepCheckPatch(BaseModel):
    step_index: int
    bullet_index: int
    checked: bool

class TimerCreate(BaseModel):
    step_index: int
    bullet_index: Optional[int] = None
    label: str
    duration_sec: int

class TimerAction(BaseModel):
    timer_id: str
    action: str  # start, pause, done, delete

class SessionPatchRequest(BaseModel):
    current_step_index: Optional[int] = None
    step_checks_patch: Optional[StepCheckPatch] = None
    timer_create: Optional[TimerCreate] = None
    timer_action: Optional[TimerAction] = None

class AssistRequest(BaseModel):
    recipe_id: str
    step_index: int
    bullet_index: Optional[int] = None
    intent: str  # substitute, macros, fix
    payload: dict

class AssistResponse(BaseModel):
    title: str
    bullets: list[str]
    confidence: Optional[float] = None
    source: str  # rules, ai, mixed


# --- Endpoints ---

@router.post("/session/start", response_model=SessionResponse)
def start_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create or return active cooking session for recipe."""
    # Check if active session exists
    existing = db.scalar(
        select(CookSession)
        .where(
            CookSession.workspace_id == workspace.id,
            CookSession.recipe_id == request.recipe_id,
            CookSession.status == "active"
        )
    )
    
    if existing:
        logger.info(f"Returning existing session {existing.id}")
        return _session_to_response(existing)
    
    # Verify recipe exists in workspace
    recipe = db.scalar(
        select(Recipe).where(
            Recipe.id == request.recipe_id,
            Recipe.workspace_id == workspace.id
        )
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Create new session
    session = CookSession(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        recipe_id=request.recipe_id,
        status="active",
        current_step_index=0,
        step_checks={},
        timers={}
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    logger.info(f"Created new cook session {session.id} for recipe {request.recipe_id}")
    return _session_to_response(session)


@router.get("/session/active", response_model=SessionResponse)
def get_active_session(
    recipe_id: str = Query(...),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get active cooking session for recipe."""
    session = db.scalar(
        select(CookSession)
        .where(
            CookSession.workspace_id == workspace.id,
            CookSession.recipe_id == recipe_id,
            CookSession.status == "active"
        )
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="No active session found")
    
    return _session_to_response(session)


@router.patch("/session/{session_id}", response_model=SessionResponse)
def patch_session(
    session_id: str,
    patch: SessionPatchRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Update cooking session state."""
    # Get session with workspace validation
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Apply patches
    if patch.current_step_index is not None:
        session.current_step_index = patch.current_step_index
    
    if patch.step_checks_patch:
        p = patch.step_checks_patch
        step_key = str(p.step_index)
        bullet_key = str(p.bullet_index)
        
        if step_key not in session.step_checks:
            session.step_checks[step_key] = {}
        
        if p.checked:
            session.step_checks[step_key][bullet_key] = True
        else:
            session.step_checks[step_key].pop(bullet_key, None)
        
        # Mark as modified for JSONB update
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "step_checks")
    
    if patch.timer_create:
        t = patch.timer_create
        timer_id = uuid.uuid4().hex
        session.timers[timer_id] = {
            "step_index": t.step_index,
            "bullet_index": t.bullet_index,
            "label": t.label,
            "duration_sec": t.duration_sec,
            "started_at": None,
            "elapsed_sec": 0,  # Track elapsed time for pause/resume
            "paused_at": None,  # NEW: Track when timer was paused
            "state": "created"
        }
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "timers")
        logger.info(f"Created timer {timer_id} in session {session_id}")
    
    if patch.timer_action:
        a = patch.timer_action
        if a.timer_id not in session.timers:
            raise HTTPException(status_code=404, detail="Timer not found")
        
        timer = session.timers[a.timer_id]
        
        if a.action == "start":
            # Starting from paused or created state
            timer["state"] = "running"
            timer["started_at"] = datetime.utcnow().isoformat() + "Z"  # Add Z for UTC
            timer["paused_at"] = None  # Clear paused timestamp
            # Keep existing elapsed_sec if resuming from pause
            if "elapsed_sec" not in timer:
                timer["elapsed_sec"] = 0
        elif a.action == "pause":
            # Calculate elapsed time and store it
            if timer.get("started_at"):
                started = datetime.fromisoformat(timer["started_at"].replace('Z', '+00:00'))
                # Make utcnow timezone-aware to match started
                now = datetime.utcnow().replace(tzinfo=started.tzinfo)
                elapsed = (now - started).total_seconds()
                current_elapsed = timer.get("elapsed_sec", 0)
                timer["elapsed_sec"] = int(current_elapsed + elapsed)
            timer["state"] = "paused"
            timer["started_at"] = None  # Clear started_at on pause
            timer["paused_at"] = datetime.utcnow().isoformat() + "Z"  # Store when paused
        elif a.action == "done":
            timer["state"] = "done"
        elif a.action == "delete":
            del session.timers[a.timer_id]
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {a.action}")
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "timers")
        logger.info(f"Timer {a.timer_id} action: {a.action}")

    
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return _session_to_response(session)


@router.patch("/session/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: str,
    action: str,  # "complete" or "abandon"
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Mark cooking session as completed or abandoned."""
    # Get session with workspace validation
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if action == "complete":
        session.status = "completed"
    elif action == "abandon":
        session.status = "abandoned"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    session.ended_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    logger.info(f"Session {session_id} marked as {session.status}")
    return _session_to_response(session)


@router.post("/assist", response_model=AssistResponse)
@limiter.limit("15/minute")
def assist(
    request: Request,  # Required for rate limiter
    assist_req: AssistRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """AI-powered cooking assistance."""
    # Verify recipe access
    recipe = db.scalar(
        select(Recipe).where(
            Recipe.id == assist_req.recipe_id,
            Recipe.workspace_id == workspace.id
        )
    )
    if not recipe:
        raise HTTPException(status_code=403, detail="Recipe not found")
    
    intent = assist_req.intent.lower()
    payload = assist_req.payload
    
    if intent == "substitute":
        # Call existing AI substitute service
        ingredient = payload.get("ingredient", "")
        if not ingredient:
            raise HTTPException(status_code=400, detail="ingredient required")
        
        # Get pantry items for context
        from ..models import PantryItem
        pantry_items = db.scalars(
            select(PantryItem).where(PantryItem.workspace_id == workspace.id)
        ).all()
        pantry_names = [item.name for item in pantry_items]
        
        result = ai_service.suggest_substitute(
            ingredient=ingredient,
            pantry_items=pantry_names,
            context=payload.get("context", "")
        )
        
        return AssistResponse(
            title=f"Substitute for {ingredient}",
            bullets=[result.substitute, result.instruction],
            confidence=_confidence_to_float(result.confidence),
            source="ai"
        )
    
    elif intent == "macros":
        # Call existing macro analysis
        ing_names = [i.name for i in recipe.ingredients]
        result = ai_service.summarize_macros(recipe.title, ing_names)
        
        tags_text = ", ".join(result.tags) if result.tags else "balanced"
        cal_text = f"{result.calories_range['min']}-{result.calories_range['max']} cal"
        
        bullets = [f"{tags_text} ({cal_text})"]
        if result.protein_range:
            bullets.append(f"Protein: {result.protein_range['min']}-{result.protein_range['max']}g")
        bullets.append(result.disclaimer)
        
        return AssistResponse(
            title="Nutritional Estimate",
            bullets=bullets,
            confidence=_confidence_to_float(result.confidence),
            source="ai"
        )
    
    elif intent == "fix":
        # Rules-first quick fixes
        problem = payload.get("problem", "").lower()
        
        fixes = {
            "too_salty": {
                "title": "Fix: Too Salty",
                "bullets": [
                    "Add acid (lemon juice, vinegar) to balance",
                    "Dilute with unsalted stock or water",
                    "Add starch (potato, rice) to absorb salt",
                ],
                "why": "Acid masks saltiness; dilution lowers concentration"
            },
            "too_spicy": {
                "title": "Fix: Too Spicy",
                "bullets": [
                    "Add dairy (cream, yogurt, cheese)",
                    "Add sweetness (honey, sugar)",
                    "Serve with cooling side (cucumber, bread)",
                ],
                "why": "Fats bind capsaicin; sweetness balances heat"
            },
            "too_thick": {
                "title": "Fix: Too Thick",
                "bullets": [
                    "Add liquid gradually (stock, water, wine)",
                    "Simmer to thin consistency",
                    "Stir frequently to prevent sticking",
                ],
                "why": "Liquid restores flow; heat helps incorporation"
            },
            "too_thin": {
                "title": "Fix: Too Thin",
                "bullets": [
                    "Simmer uncovered to reduce",
                    "Add starch slurry (cornstarch + water)",
                    "Add pureed vegetables or cream",
                ],
                "why": "Evaporation concentrates; starches thicken"
            },
        }
        
        fix = fixes.get(problem)
        if not fix:
            return AssistResponse(
                title="General Cooking Tips",
                bullets=["Taste frequently", "Adjust gradually", "Use fresh ingredients"],
                source="rules"
            )
        
        bullets = fix["bullets"] + [f"Why: {fix['why']}"]
        
        return AssistResponse(
            title=fix["title"],
            bullets=bullets,
            confidence=0.9,
            source="rules"
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")


# --- Helpers ---

def _session_to_response(session: CookSession) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        recipe_id=session.recipe_id,
        status=session.status,
        started_at=session.started_at.isoformat(),
        current_step_index=session.current_step_index,
        step_checks=session.step_checks,
        timers=session.timers,
    )

def _confidence_to_float(conf_str: str) -> float:
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(conf_str, 0.5)
