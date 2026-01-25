"""Cook session API router for Cook Assist v1.

Endpoints:
- POST /session/start - Create or return active session
- GET /session/active - Get active session for recipe
- PATCH /session/{id} - Update session state
- POST /assist - AI-powered cooking assistance
"""

import uuid
import logging
import asyncio
import queue
import json
from typing import Optional, List
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field

from ..db import get_db
from ..deps import get_workspace
from ..models import Workspace, CookSession, Recipe
from ..services.ai_service import ai_service
from ..services.variant_generator import variant_generator
from ..services.cook_adjustments import generate_adjustment
from ..schemas import (
    MethodListResponse, MethodPreviewRequest, MethodApplyRequest, MethodPreviewResponse,
    SessionResponse, SessionPatchRequest,
    AdjustPreviewRequest, AdjustPreviewResponse, AdjustApplyRequest
)

router = APIRouter(prefix="/cook", tags=["cook"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("tasteos.cook")

# --- SSE PubSub ---
# session_id -> list of queues
_session_listeners: dict[str, list[queue.Queue]] = defaultdict(list)

def notify_session_update(session: CookSession):
    """Publish session update to all active listeners."""
    try:
        data = session_to_response(session).model_dump(mode='json')
        msg = f"event: session\ndata: {json.dumps(data)}\n\n"
        
        listeners = _session_listeners.get(session.id, [])
        dead_queues = []
        for q in listeners:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead_queues.append(q)
        
        # Cleanup full/dead queues
        for dq in dead_queues:
            if dq in listeners:
                listeners.remove(dq)
                
    except Exception as e:
        logger.error(f"Failed to publish session update: {e}")



# --- Request/Response Models ---

class SessionStartRequest(BaseModel):
    recipe_id: str

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
        return session_to_response(existing)
    
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
        servings_base=recipe.servings or 1,
        servings_target=recipe.servings or 1,
        current_step_index=0,
        step_checks={},
        timers={}
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    logger.info(f"Created new cook session {session.id} for recipe {request.recipe_id}")
    return session_to_response(session)


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
    
    return session_to_response(session)

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
    if patch.servings_target is not None:
        session.servings_target = patch.servings_target

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
    
    notify_session_update(session)
    return session_to_response(session)


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
    
    notify_session_update(session)
    logger.info(f"Session {session_id} marked as {session.status}")
    return session_to_response(session)


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


@router.get("/session/{session_id}/events")
async def session_events(
    request: Request,
    session_id: str,
    # db: Session = Depends(get_db), # NOTE: Standard validation skipped for stream performance unless strict is needed
):
    """Server-Sent Events for session updates."""
    
    async def event_generator():
        q = queue.Queue(maxsize=20)
        _session_listeners[session_id].append(q)
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                try:
                    # Non-blocking get with loop yielding
                    # We run q.get in executor if we want strict non-blocking, but q.get_nowait + sleep is often simpler for low throughput
                    # Better: await loop.run_in_executor
                    loop = asyncio.get_running_loop()
                    try:
                         # Wait for event with timeout for keepalive
                        data = await asyncio.wait_for(
                             loop.run_in_executor(None, q.get, True, 5), # timeout 5s within executor? No, q.get(block=True, timeout=5)
                             timeout=15 
                        )
                        yield data
                    except asyncio.TimeoutError:
                         # Keepalive
                         yield "event: ping\ndata: {}\n\n"
                    except queue.Empty:
                         yield "event: ping\ndata: {}\n\n"
                         
                except Exception as e:
                    # logger.error(f"SSE Error: {e}")
                    yield "event: ping\ndata: {}\n\n"
                    await asyncio.sleep(5) # Avoid tight loop on error
                    
        finally:
            if q in _session_listeners[session_id]:
                _session_listeners[session_id].remove(q)
            # logger.info(f"SSE client disconnected for {session_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")



# --- Method Switcher Endpoints ---

@router.get("/methods", response_model=MethodListResponse)
def get_supported_methods(
    request: Request,
    workspace: Workspace = Depends(get_workspace),
):
    """Get available cooking methods for Method Switching."""
    methods = variant_generator.get_supported_methods()
    return MethodListResponse(methods=methods)


@router.post("/session/{session_id}/method/preview", response_model=MethodPreviewResponse)
def preview_method_variant(
    session_id: str,
    body: MethodPreviewRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Generate a preview of the recipe variant for the selected method."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        preview = variant_generator.generate(recipe, body.method_key)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/method/apply", response_model=SessionResponse)
def apply_method_variant(
    session_id: str,
    body: MethodApplyRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Apply a method override to the session."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update session
    session.method_key = body.method_key
    session.steps_override = body.steps_override
    session.method_tradeoffs = body.method_tradeoffs
    session.method_generated_at = datetime.utcnow()
    
    # Reset progress as we are back to original steps (or new steps)
    session.current_step_index = 0
    session.step_checks = {} 

    db.commit()
    db.refresh(session)
    
    notify_session_update(session)
    return session_to_response(session)


@router.post("/session/{session_id}/method/reset", response_model=SessionResponse)
def reset_method_variant(
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Clear any method overrides and return to original recipe."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.method_key = None
    session.steps_override = None
    session.method_tradeoffs = None
    session.method_generated_at = None
    
    # Reset progress
    session.current_step_index = 0
    session.step_checks = {}

    db.commit()
    db.refresh(session)
    
    notify_session_update(session)
    return session_to_response(session)


# --- Adjust On The Fly Endpoints ---

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
    """Apply a step adjustment permanently to the session."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.steps_override = request.steps_override
    
    # Append to log
    # request.adjustment is a Pydantic model CookAdjustment
    log_entry = request.adjustment.model_dump(mode='json')
    log_entry["applied_at"] = datetime.utcnow().isoformat()
    
    if not session.adjustments_log:
        session.adjustments_log = []
        
    session.adjustments_log.append(log_entry)
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "adjustments_log")
    flag_modified(session, "steps_override")
    
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    notify_session_update(session)
    return session_to_response(session)


# --- Helpers ---

def session_to_response(session: CookSession) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        recipe_id=session.recipe_id,
        status=session.status,
        started_at=session.started_at.isoformat(),
        servings_base=session.servings_base,
        servings_target=session.servings_target,
        current_step_index=session.current_step_index,
        step_checks=session.step_checks,
        timers=session.timers,
        method_key=session.method_key,
        steps_override=session.steps_override,
        method_tradeoffs=session.method_tradeoffs,
        method_generated_at=session.method_generated_at,
        adjustments_log=session.adjustments_log or [],
    )

def _confidence_to_float(conf_str: str) -> float:
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(conf_str, 0.5)
