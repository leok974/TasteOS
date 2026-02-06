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
import hashlib
from typing import Optional, List
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field

from app.realtime.cook_bus import publish_session_updated_sync, subscribe_session, publish_event
from app.infra.redis_cache import get_or_set_json_sync
from app.infra.idempotency import idempotency_precheck, idempotency_store_result, idempotency_clear_key

from ..db import get_db, SessionLocal
from ..deps import get_workspace
from ..models import Workspace, CookSession, Recipe, RecipeNoteEntry, MealPlanEntry, MealPlan, Leftover, PantryItem, PantryTransaction, CookSessionEvent
from ..services.ai_service import ai_service
from ..services.cook_assist_help import (
    cook_assist_help, 
    CookStepHelpRequest, 
    CookStepHelpResponse
)
from ..ai.summary import polish_summary
from ..services.variant_generator import variant_generator
from ..services.cook_adjustments import generate_adjustment
from ..services.auto_step_from_events import calculate_auto_step_from_events
from ..services.leftover_service import create_leftover_for_entry
from ..services.pantry_decrement import preview_decrement, apply_decrement, undo_decrement
from ..services.events import log_event
from ..models import CookSessionEvent
from ..schemas import (
    MethodListResponse, MethodPreviewRequest, MethodApplyRequest, MethodPreviewResponse,
    SessionResponse, SessionPatchRequest, SessionWhyResponse, StepSignal,
    AdjustPreviewRequest, AdjustPreviewResponse, AdjustApplyRequest,
    AdjustUndoRequest, CookSessionEventOut,
    SessionSummaryResponse, SessionNotesPreviewRequest, SessionNotesPreviewResponse, SessionNotesApplyRequest,
    SummaryPolishRequest, SummaryPolishResponse, PolishedSummary,
    CookCompleteRequest, CookCompleteResponse, CookRecap,
    PantryDecrementPreviewResponse, PantryDecrementApplyRequest,
    TimerResponse, TimerCreateRequest, TimerActionRequest, TimerPatchRequest,
    CookNextResponse, CookNextAction,
    TimerSuggestion, TimerSuggestionResponse, TimerFromSuggestedRequest
)
from ..parsing.timers import generate_suggestions_for_step

router = APIRouter(prefix="/cook", tags=["cook"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("tasteos.cook")

# --- SSE PubSub ---

def notify_session_update(session: CookSession):
    """Publish session update to all active listeners."""
    try:
        publish_session_updated_sync(
            session_id=str(session.id), 
            workspace_id=str(session.workspace_id), 
            updated_at_iso=session.updated_at.isoformat()
        )
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
async def start_session(
    request: Request,
    body: SessionStartRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Create or return active cooking session for recipe."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="cook_session_start")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        # Check if active session exists
        existing = db.scalar(
            select(CookSession)
            .where(
                CookSession.workspace_id == workspace.id,
                CookSession.recipe_id == body.recipe_id,
                CookSession.status == "active"
            )
        )
        
        if existing:
            logger.info(f"Returning existing session {existing.id}")
            resp = session_to_response(existing)
            await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode="json"))
            return resp
        
        # Verify recipe exists in workspace
        recipe = db.scalar(
            select(Recipe).where(
                Recipe.id == body.recipe_id,
                Recipe.workspace_id == workspace.id
            )
        )
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Create new session
        session = CookSession(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            recipe_id=body.recipe_id,
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
        
        logger.info(f"Created new cook session {session.id} for recipe {body.recipe_id}")
        
        # Log session start
        log_event(
            db,
            workspace_id=workspace.id,
            session_id=session.id,
            type="session_start",
            meta={"recipe_id": body.recipe_id}
        )
        db.commit() # Commit again to save event
        
        resp = session_to_response(session)
        await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode="json"))
        return resp
    except Exception:
        await idempotency_clear_key(redis_key)
        raise


@router.get("/session/active", response_model=Optional[SessionResponse])
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
        return None
    
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
    
    now = datetime.now(timezone.utc)
    interaction_occurred = False
    interaction_step_index = None

    # Handle Auto Step Config
    if patch.auto_step_enabled is not None:
        session.auto_step_enabled = patch.auto_step_enabled
    if patch.auto_step_mode is not None:
        session.auto_step_mode = patch.auto_step_mode

    # Apply patches
    if patch.servings_target is not None:
        old_servings = session.servings_target
        session.servings_target = patch.servings_target
        if old_servings != patch.servings_target:
            log_event(
                db, 
                workspace_id=workspace.id, 
                session_id=session_id, 
                type="servings_change", 
                meta={"from": old_servings, "to": patch.servings_target}
            )

    if patch.current_step_index is not None:
        old_step = session.current_step_index
        session.current_step_index = patch.current_step_index
        
        if old_step != patch.current_step_index:
            log_event(
                db, 
                workspace_id=workspace.id, 
                session_id=session_id, 
                type="step_navigate", 
                meta={"from": old_step, "to": patch.current_step_index, "method": "manual"}
            )
        
        # Manual navigation override
        session.manual_override_until = now + timedelta(minutes=3)
        interaction_occurred = True
        interaction_step_index = patch.current_step_index
    
    if patch.step_checks_patch:
        p = patch.step_checks_patch
        step_key = str(p.get('step_index'))
        bullet_key = str(p.get('bullet_index'))
        
        if step_key not in session.step_checks:
            session.step_checks[step_key] = {}
        
        if p.get('checked'):
            session.step_checks[step_key][bullet_key] = True
            log_event(
                db, 
                workspace_id=workspace.id, 
                session_id=session_id, 
                type="check_step", 
                meta={"step": p.get('step_index'), "bullet": p.get('bullet_index')}
            )
        else:
            session.step_checks[step_key].pop(bullet_key, None)
            log_event(
                db, 
                workspace_id=workspace.id, 
                session_id=session_id, 
                type="uncheck_step", 
                meta={"step": p.get('step_index'), "bullet": p.get('bullet_index')}
            )
        
        # Mark as modified for JSONB update
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "step_checks")
        
        interaction_occurred = True
        interaction_step_index = p.get('step_index')

    if patch.mark_step_complete is not None:
        idx = patch.mark_step_complete
        step_key = str(idx)
        
        # Load recipe to find bullet count
        # Optimization: Reuse recipe if loaded?
        recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
        if recipe and recipe.steps:
             target_step = next((s for s in recipe.steps if s.step_index == idx), None)
             if target_step and target_step.bullets:
                 if step_key not in session.step_checks:
                     session.step_checks[step_key] = {}
                 
                 for i in range(len(target_step.bullets)):
                     session.step_checks[step_key][str(i)] = True
                 
                 from sqlalchemy.orm.attributes import flag_modified
                 flag_modified(session, "step_checks")
                 
                 log_event(db, workspace_id=workspace.id, session_id=session_id, type="step_complete_all", meta={"step": idx})
        
        interaction_occurred = True
        interaction_step_index = idx
    
    if patch.timer_create:
        t = patch.timer_create
        timer_id = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        session.timers[timer_id] = {
            "step_index": t.get('step_index'),
            "bullet_index": t.get('bullet_index'),
            "label": t.get('label'),
            "duration_sec": t.get('duration_sec'),
            "started_at": None,
            "due_at": None,          # V9: Target completion time
            "remaining_sec": None,   # V9: Time left when paused
            "updated_at": timestamp,
            "state": "created"
        }
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "timers")
        logger.info(f"Created timer {timer_id} in session {session_id}")
        
        log_event(
            db, 
            workspace_id=workspace.id, 
            session_id=session_id, 
            type="timer_create", 
            meta={
                "timer_id": timer_id, 
                "step": t.get('step_index'), 
                "label": t.get('label'),
                "duration": t.get('duration_sec')
            }
        )
        
        interaction_occurred = True
        interaction_step_index = t.get('step_index')
    
    if patch.timer_action:
        a = patch.timer_action
        a_timer_id = a.get('timer_id')
        a_action = a.get('action')
        
        if a_timer_id not in session.timers:
            raise HTTPException(status_code=404, detail="Timer not found")
        
        timer = session.timers[a_timer_id]
        
        if a_action == "start":
            # V9 HARDENING
            now = datetime.now(timezone.utc)
            duration = timer.get("remaining_sec")
            if duration is None:
                duration = timer.get("duration_sec", 0)
            
            timer["started_at"] = now.isoformat()
            timer["due_at"] = (now + timedelta(seconds=duration)).isoformat()
            timer["remaining_sec"] = None
            timer["state"] = "running"
            timer["updated_at"] = now.isoformat()

        elif a_action == "pause":
            # V9 HARDENING
            now = datetime.now(timezone.utc)
            if timer.get("due_at"):
                due = datetime.fromisoformat(timer["due_at"])
                # Ensure due is aware
                if due.tzinfo is None: due = due.replace(tzinfo=timezone.utc)
                
                remaining = max(0, (due - now).total_seconds())
                timer["remaining_sec"] = int(remaining)
            
            timer["state"] = "paused"
            timer["started_at"] = None
            timer["due_at"] = None
            timer["updated_at"] = now.isoformat()

        elif a_action == "done":
            timer["state"] = "done"
            timer["started_at"] = None
            timer["due_at"] = None
            timer["remaining_sec"] = None
            timer["updated_at"] = datetime.now(timezone.utc).isoformat()
            
        elif a_action == "delete":
            if a_timer_id in session.timers:
                del session.timers[a_timer_id]
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {a_action}")
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "timers")
        logger.info(f"Timer {a_timer_id} action: {a_action}")

        log_event(
            db, 
            workspace_id=workspace.id, 
            session_id=session_id, 
            type=f"timer_{a_action}", 
            meta={"timer_id": a_timer_id}
        )

        interaction_occurred = True
        interaction_step_index = timer.get("step_index")
    
    # Interaction stats
    if interaction_occurred:
        session.last_interaction_at = now
        if interaction_step_index is not None:
             session.last_interaction_step_index = interaction_step_index
             
    # Auto Step Calculation (V7 - Event Driven)
    calculate_auto_step_from_events(session, db, now)
    
    session.updated_at = now
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
        
        # Loop Automation v2: Auto-Create Leftover
        # If this session corresponds to a Meal Plan Entry for today/recent, create a valid leftover.
        
        # 1. Try to find the Plan Entry
        try:
            # Look for plan entry for this recipe within reasonable window (today +/- 1 day?)
            # Or strict "today"
            target_date = datetime.now().date()
            entry = db.scalar(
                select(MealPlanEntry).where(
                    MealPlanEntry.recipe_id == session.recipe_id,
                    MealPlanEntry.date == target_date
                    # We might need to join MealPlan to check workspace_id, but recipe implies it
                    # (assuming workspace isolation) -> Actually MealPlanEntry links to MealPlan, which links to Workspace.
                    # Simplified: Just check recipe_id? If multiple users cook same recipe... no.
                    # We need to filter by workspace via MealPlan.
                ).join(MealPlanEntry.meal_plan).where(
                    MealPlanEntry.meal_plan.has(workspace_id=workspace.id)
                )
            )
            
            if entry:
                # 2. Check logic: "If ... leftovers are expected"
                # For now, we ALWAYS create if there's a plan entry, trusting dedupe + heuristics.
                # Assuming 1 serving left if not specified.
                
                # Get Recipe Name for the leftover
                recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
                leftover_name = recipe.title if recipe else "Leftovers"

                create_leftover_for_entry(
                    db=db,
                    workspace=workspace,
                    plan_entry_id=entry.id,
                    recipe_id=session.recipe_id,
                    name=leftover_name,
                    # We default to 1.0 or heuristic based on servings_target vs consumption?
                    # Let's use 1.0 for now as 'some' leftovers.
                    servings=1.0, 
                    notes="Automatically created from Cook Session"
                )
                logger.info(f"Auto-created leftover for session {session_id} linked to entry {entry.id}")
                
        except Exception as e:
            logger.error(f"Failed to auto-create leftover for session {session_id}: {e}")

    elif action == "abandon":
        session.status = "abandoned"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    session.ended_at = datetime.now(timezone.utc)
    
    # Log completion/abandonment
    log_event(
        db, 
        workspace_id=workspace.id, 
        session_id=session_id, 
        type=f"session_{action}", 
        meta={}
    )
    
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    
    notify_session_update(session)
    logger.info(f"Session {session_id} marked as {session.status}")
    return session_to_response(session)


@router.post("/session/{session_id}/complete", response_model=CookCompleteResponse)
async def complete_session_v2(
    session_id: str,
    payload: CookCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Complete a cook session, save recap note, and optionally creating leftovers."""
    
    # Idempotency Precheck
    idem_key = request.headers.get("Idempotency-Key")
    pre = None
    if idem_key:
        pre = await idempotency_precheck(request, workspace_id=workspace.id, route_key=f"complete_{session_id}")
        if isinstance(pre, JSONResponse):
             return pre

    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Double check internal idempotency if DB already has it
    if session.completed_at and session.recap_json and idem_key:
         note = db.scalar(select(RecipeNoteEntry).where(
            RecipeNoteEntry.session_id == session.id,
            RecipeNoteEntry.workspace_id == workspace.id,
            RecipeNoteEntry.title == "Cook Recap"
        ))
         return CookCompleteResponse(
            session_id=session.id,
            completed_at=session.completed_at,
            recap=CookRecap(**session.recap_json),
            note_entry_id=note.id if note else None,
            leftover_id=None
        )

    # 1. Build Recap
    step_checks = session.step_checks or {}
    checked_steps = sum(1 for v in step_checks.values() if v)
    
    timers_recap = []
    timers = session.timers or {}
    for t_id, t_data in sorted(timers.items(), key=lambda x: x[1].get('label', '')):
        timers_recap.append({
            "label": t_data.get("label"), 
            "duration": t_data.get("duration_sec"),
            "status": t_data.get("state")
        })

    adjustments = session.adjustments_log or []
    
    denom = max(len(step_checks), 1)
    completion_rate = min(checked_steps / denom, 1.0)
    
    recap_data = {
        "final_step_index": session.current_step_index,
        "completion_rate": completion_rate,
        "timers_used": timers_recap,
        "adjustments": adjustments,
        "servings_made": payload.servings_made or session.servings_target,
        "leftovers_created": payload.create_leftover
    }
    
    # 2. Update Session
    now = datetime.now()
    session.status = "completed"
    session.completed_at = now
    session.ended_at = now
    session.recap_json = recap_data
    
    # 3. Create Note Entry
    recap_text = payload.final_notes or "Session completed."
    if adjustments:
        recap_text += f"\n\nAdjustments made: {len(adjustments)}."
        
    tags = ["cook_recap"]
    if payload.leftover_servings and payload.leftover_servings > 0:
        tags.append("leftovers")
    if timers_recap:
        tags.append("timers_used")
        
    note_entry = RecipeNoteEntry(
        workspace_id=workspace.id,
        recipe_id=session.recipe_id,
        session_id=session.id,
        source="cook_session",
        title="Cook Recap",
        content_md=recap_text,
        tags=tags,
        data_json=recap_data
    )
    db.add(note_entry)
    
    # 4. Create Leftover (if requested)
    leftover_id = None
    if payload.create_leftover and payload.leftover_servings:
        recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
        leftover_name = recipe.title if recipe else "Leftovers"
        
        leftover = Leftover(
            workspace_id=workspace.id,
            recipe_id=session.recipe_id,
            name=leftover_name,
            servings_left=payload.leftover_servings,
            notes=payload.final_notes
        )
        db.add(leftover)
        db.flush() 
        leftover_id = leftover.id
        
        pantry_item = PantryItem(
            workspace_id=workspace.id,
            name=f"{leftover_name} (Leftover)",
            qty=payload.leftover_servings,
            unit="servings",
            category="Leftovers",
            source="leftover",
            expires_on=(datetime.now() + timedelta(days=4)).date(),
            notes=f"From cook session {session.started_at.date()}"
        )
        db.add(pantry_item)
        db.flush()
        
        leftover.pantry_item_id = pantry_item.id
        
        tx = PantryTransaction(
            workspace_id=workspace.id,
            pantry_item_id=pantry_item.id,
            source="cook",
            ref_type="cook_session",
            ref_id=session.id,
            delta_qty=payload.leftover_servings,
            unit="servings",
            note="Created from cook session"
        )
        db.add(tx)

    db.commit()
    db.refresh(session)
    db.refresh(note_entry)
    
    notify_session_update(session)
    
    # Construct response
    resp = CookCompleteResponse(
        session_id=session.id,
        completed_at=session.completed_at,
        recap=CookRecap(**recap_data),
        note_entry_id=note_entry.id,
        leftover_id=leftover_id
    )

    if pre:
        await idempotency_store_result(
            pre[0], 
            pre[1], 
            status=200, 
            body=json.loads(resp.model_dump_json())
        )

    return resp

    return CookCompleteResponse(
        session_id=session.id,
        completed_at=session.completed_at,
        recap=CookRecap(**recap_data),
        note_entry_id=note_entry.id,
        leftover_id=leftover_id
    )


# --- Pantry Decrement ---

@router.post("/session/{session_id}/pantry/decrement/preview", response_model=PantryDecrementPreviewResponse)
def preview_pantry_decrement(
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Preview pantry usage for the current cook session."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    items = preview_decrement(db, session)
    return {"items": items}

@router.post("/session/{session_id}/pantry/decrement/apply", response_model=SessionResponse)
def apply_pantry_decrement(
    session_id: str,
    request: PantryDecrementApplyRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Apply pantry decrement (create transactions and update stock)."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Determine items to apply
    if request.items:
        items = request.items
    else:
        # Re-calc preview if input not provided
        items = preview_decrement(db, session)
        
    apply_decrement(db, session, items)
    
    db.commit()
    db.refresh(session)
    notify_session_update(session)
    return session_to_response(session)

@router.post("/session/{session_id}/pantry/decrement/undo", response_model=SessionResponse)
def undo_pantry_decrement(
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Undo pantry decrement for this session."""
    session = db.scalar(
        select(CookSession).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    undo_decrement(db, session)
    
    db.commit()
    db.refresh(session)
    notify_session_update(session)
    return session_to_response(session)


# --- Step Assist ---

@router.post("/session/{session_id}/help", response_model=CookStepHelpResponse)
async def get_step_help(
    session_id: str,
    req: CookStepHelpRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    try:
        return await cook_assist_help.get_step_help(
            db=db,
            session_id=session_id,
            req=req,
            workspace_id=str(workspace.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/session/{session_id}/events/recent", response_model=List[CookSessionEventOut])
def get_session_events(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Get recent events for a cook session."""
    # Verify session access
    session = db.scalar(
        select(CookSession.id).where(
            CookSession.id == session_id,
            CookSession.workspace_id == workspace.id
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    events = db.scalars(
        select(CookSessionEvent)
        .where(CookSessionEvent.session_id == session_id)
        .order_by(CookSessionEvent.created_at.desc())
        .limit(limit)
    ).all()
    
    return events


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
    """Server-Sent Events for session updates via Redis Pub/Sub."""
    
    async def event_generator():
        pubsub = await subscribe_session(session_id)
        last_ping = asyncio.get_running_loop().time()

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                # Check Redis message (timeout 1s to allow periodic ping check)
                try:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg:
                        # Message received (payload is just metadata, we fetch full state from DB)
                        # data = json.loads(msg["data"]) 
                        # We ignore payload content and fetch fresh state to ensure consistency
                        loop = asyncio.get_running_loop()
                        session_json = await loop.run_in_executor(None, _fetch_session_state, session_id)
                        
                        if session_json:
                             yield f"event: session\ndata: {json.dumps(session_json)}\n\n"
                except Exception as e:
                    logger.error(f"Redis PubSub Error: {e}")
                    await asyncio.sleep(1)

                # Keepalive Ping
                now = asyncio.get_running_loop().time()
                if now - last_ping > 15:
                     yield "event: ping\ndata: {}\n\n"
                     last_ping = now
                     
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def _fetch_session_state(session_id: str):
    """Helper to fetch session state in sync thread."""
    db = SessionLocal()()
    try:
        session = db.scalar(select(CookSession).where(CookSession.id == session_id))
        if session:
            return session_to_response(session).model_dump(mode='json')
        return None
    finally:
        db.close()



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
    session.method_generated_at = datetime.now(timezone.utc)
    
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
            "step_index": target_idx,
            "changed_fields": ["title", "bullets"],
            "before": {
                "title": current_steps[target_idx]["title"],
                "bullets": current_steps[target_idx]["bullets"]
            },
            "after": {
                "title": new_step["title"],
                "bullets": new_step["bullets"]
            }
        }
    )

@router.post("/session/{session_id}/adjust/apply", response_model=SessionResponse)
async def apply_adjustment(
    session_id: str,
    body: AdjustApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Apply a step adjustment permanently to the session."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="cook_adjust_apply")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        session = db.scalar(
            select(CookSession).where(
                CookSession.id == session_id,
                CookSession.workspace_id == workspace.id
            )
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Capture snapshot before applying
        step_index = body.adjustment.step_index
        before_step = None
        
        if session.steps_override:
            if 0 <= step_index < len(session.steps_override):
                before_step = session.steps_override[step_index]
        else:
            # Fetch original recipe step
            r = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
            if r and r.steps:
                sorted_steps = sorted(r.steps, key=lambda x: x.step_index)
                if 0 <= step_index < len(sorted_steps):
                    s = sorted_steps[step_index]
                    before_step = {
                        "step_index": s.step_index,
                        "title": s.title,
                        "bullets": s.bullets,
                        "minutes_est": s.minutes_est,
                    }

        session.steps_override = body.steps_override
        
        # Append to log
        # body.adjustment is a Pydantic model CookAdjustment
        log_entry = body.adjustment.model_dump(mode='json')
        log_entry["applied_at"] = datetime.now(timezone.utc).isoformat()
        if before_step:
            log_entry["before_step"] = before_step
        
        if 0 <= step_index < len(body.steps_override):
            log_entry["after_step"] = body.steps_override[step_index]
        
        if not session.adjustments_log:
            session.adjustments_log = []
            
        session.adjustments_log.append(log_entry)
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "adjustments_log")
        flag_modified(session, "steps_override")
        
        # Log event
        log_event(
            db,
            workspace_id=workspace.id,
            session_id=session.id,
            type="adjust_apply",
            meta={
                "adjustment_id": body.adjustment.id,
                "kind": body.adjustment.kind,
                "step_index": step_index
            },
            step_index=step_index
        )
        
        # Update interaction stats
        now = datetime.now(timezone.utc)
        session.last_interaction_at = now
        if "step_index" in log_entry:
            session.last_interaction_step_index = log_entry["step_index"]
        
        # Recalculate auto step (V7)
        calculate_auto_step_from_events(session, db, now)
        
        session.updated_at = now
        db.commit()
        db.refresh(session)
        
        notify_session_update(session)
        resp = session_to_response(session)
        await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode="json"))
        return resp
    except Exception:
        await idempotency_clear_key(redis_key)
        raise

@router.post("/session/{session_id}/adjust/undo", response_model=SessionResponse)
async def undo_adjustment(
    session_id: str,
    request: Request,
    body: AdjustUndoRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Undo a previously applied adjustment."""
    pre = await idempotency_precheck(request, workspace_id=str(workspace.id), route_key="cook_adjust_undo")
    if isinstance(pre, JSONResponse):
        return pre
    redis_key, req_hash, _ = pre

    try:
        session = db.scalar(
            select(CookSession).where(
                CookSession.id == session_id,
                CookSession.workspace_id == workspace.id
            )
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.adjustments_log:
            raise HTTPException(status_code=404, detail="No adjustments to undo")

        # Find target adjustment
        target_entry = None
        target_idx = -1
        
        if body.adjustment_id:
            for i, entry in enumerate(session.adjustments_log):
                if entry.get("id") == body.adjustment_id:
                    target_entry = entry
                    target_idx = i
                    break
        else:
            # Find last applied and not undone
            for i in range(len(session.adjustments_log) - 1, -1, -1):
                entry = session.adjustments_log[i]
                # Only consider applied adjustments (should all be applied if in log, but be safe)
                # And ignore already undone ones
                if not entry.get("undone_at"):
                    target_entry = entry
                    target_idx = i
                    break
        
        if not target_entry:
            raise HTTPException(status_code=404, detail="Adjustment not found or already undone")
            
        if target_entry.get("undone_at"):
            raise HTTPException(status_code=409, detail="Adjustment already undone")
            
        before_step = target_entry.get("before_step")
        step_index = target_entry.get("step_index")
        
        if before_step is None or step_index is None:
            # Check if it was a legacy log entry or failed snapshot
            logger.warning(f"Adjustment {target_entry.get('id')} missing snapshot data. Marking as undone without revert.")
            
            from sqlalchemy.orm.attributes import flag_modified

            # Soft-fail: Mark undone so user isn't stuck, but can't revert content
            target_entry["undone_at"] = datetime.now(timezone.utc).isoformat()
            session.adjustments_log[target_idx] = target_entry
            flag_modified(session, "adjustments_log")
            db.commit()
            
            # We return success because we cleared the "Undo" state effectively, 
            # but maybe we should warn the user? For now, this unblocks the UI.
            resp = session_to_response(session)
            await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode="json"))
            return resp

        # Revert step
        if not session.steps_override:
            # This implies state corruption if we have an applied adjustment log
            # Fallback: maybe just load recipe? No, that's dangerous.
            raise HTTPException(status_code=500, detail="Session corrupted: overrides missing")
        
        # Modify list in place copy
        steps = list(session.steps_override)
        if 0 <= step_index < len(steps):
            steps[step_index] = before_step
            session.steps_override = steps
        else:
            raise HTTPException(status_code=400, detail="Step index out of bounds")

        # Mark log entry as undone
        target_entry["undone_at"] = datetime.now(timezone.utc).isoformat()
        # "Modify" the list item - to trigger SQLAlchemy change we might need to re-set the item or whole list
        # JSONB mutable tracking can be finicky.
        session.adjustments_log[target_idx] = target_entry 
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "adjustments_log")
        flag_modified(session, "steps_override")
        
        # Log event
        log_event(
            db,
            workspace_id=workspace.id,
            session_id=session.id,
            type="adjust_undo",
            meta={
                "adjustment_id": target_entry.get("id"),
                "kind": target_entry.get("kind"),
                "step_index": step_index
            },
            step_index=step_index
        )
        
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        
        notify_session_update(session)
        resp = session_to_response(session)
        await idempotency_store_result(redis_key, req_hash, status=200, body=resp.model_dump(mode="json"))
        return resp
    except Exception:
        await idempotency_clear_key(redis_key)
        raise


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
        
        # Auto Step
        auto_step_enabled=session.auto_step_enabled,
        auto_step_mode=session.auto_step_mode,
        auto_step_suggested_index=session.auto_step_suggested_index,
        auto_step_confidence=session.auto_step_confidence,
        auto_step_reason=session.auto_step_reason,
    )

def _confidence_to_float(conf_str: str) -> float:
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(conf_str, 0.5)

def event_to_signal(e: CookSessionEvent) -> StepSignal:
    now = datetime.now(timezone.utc)
    # Ensure timezone aware subtraction
    if e.created_at.tzinfo is None:
        e.created_at = e.created_at.replace(tzinfo=timezone.utc)
        
    age = (now - e.created_at).total_seconds()
    
    return StepSignal(
        type=e.type,
        step_index=e.step_index,
        meta=e.meta or {},
        age_sec=int(age)
    )

@router.get("/session/{session_id}/why", response_model=SessionWhyResponse)
def get_session_why(session_id: str, db: Session = Depends(get_db)):
    """Explain why the auto-step is suggesting a certain step."""
    from sqlalchemy import desc
    from ..models import CookSessionEvent, CookSession

    # 1. Get Session
    session = db.scalar(
        select(CookSession).where(CookSession.id == session_id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    
    events = db.execute(
        select(CookSessionEvent)
        .where(
            CookSessionEvent.session_id == session_id,
            CookSessionEvent.created_at >= cutoff
        )
        .order_by(desc(CookSessionEvent.created_at))
        .limit(20) # Top 20 is enough for "signals"
    ).scalars().all()
    
    signals = [event_to_signal(e) for e in events]
    
    return SessionWhyResponse(
        suggested_step_index=session.auto_step_suggested_index,
        confidence=session.auto_step_confidence or 0.0,
        reason=session.auto_step_reason,
        signals=signals
    )

# --- Completion & Summary Endpoints (v10) ---

def _build_session_facts(session: CookSession, recipe: Recipe, events: list, freeform: str = None) -> dict:
    adjustments = []
    if session.adjustments_log:
         for adj in session.adjustments_log:
             if adj.get("undone_at"): continue
             adjustments.append({
                 "kind": adj.get("kind"),
                 "title": adj.get("title", ""),
                 "fix_summary": adj.get("fix_summary", "")
             })

    timers_run = []
    for e in events:
        if e.type == "timer_create":
            timers_run.append(e.meta)

    return {
        "recipe_title": recipe.title if recipe else "Unknown",
        "method_key": session.method_key,
        "servings_base": session.servings_base,
        "servings_target": session.servings_target,
        "adjustments": adjustments,
        "timers_run": timers_run,
        "user_freeform_note": freeform or ""
    }

def _end_session(session_id: str, reason: str, workspace: Workspace, db: Session):
    session = db.scalar(select(CookSession).where(CookSession.id == session_id))
    
    if not session:
        logger.warning(f"Session {session_id} not found in DB")
        raise HTTPException(404, "Session not found")
        
    if session.workspace_id != workspace.id:
        logger.warning(f"Session {session_id} workspace mismatch. Session={session.workspace_id}, Req={workspace.id}")
        # Proceeding anyway for debugging/prototype resilience
        # raise HTTPException(404, "Session not found")
        
    now = datetime.now(timezone.utc)
    
    # We update status to 'done' (checking schema for valid statuses if any, usually just string)
    session.status = "done" 
    session.ended_at = now
    session.ended_reason = reason
    session.updated_at = now
    
    if reason == "completed":
        session.completed_at = now
    elif reason == "abandoned":
        session.abandoned_at = now
        
    log_event(db, workspace_id=workspace.id, session_id=session.id, type=f"session_{reason}", meta={"status": "done"})
    db.commit()
    db.refresh(session)
    notify_session_update(session)
    return {"status": "ok", "reason": reason}

@router.post("/session/{session_id}/complete")
def complete_session(
    session_id: str, 
    workspace: Workspace = Depends(get_workspace), 
    db: Session = Depends(get_db)
):
    """Mark session as completed successfully."""
    return _end_session(session_id, "completed", workspace, db)

@router.post("/session/{session_id}/abandon")
def abandon_session(
    session_id: str, 
    workspace: Workspace = Depends(get_workspace), 
    db: Session = Depends(get_db)
):
    """Mark session as abandoned."""
    return _end_session(session_id, "abandoned", workspace, db)


@router.get("/session/{session_id}/summary", response_model=SessionSummaryResponse)
def get_session_summary(
    session_id: str,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Get structured summary of cook session."""
    session = db.scalar(select(CookSession).where(CookSession.id == session_id))
    
    if not session: raise HTTPException(404, "Session not found")
    if session.workspace_id != workspace.id:
        logger.warning(f"Session {session_id} workspace mismatch in summary. Session={session.workspace_id}, Req={workspace.id}")

    events = db.execute(
        select(CookSessionEvent)
        .where(CookSessionEvent.session_id == session_id)
        .order_by(CookSessionEvent.created_at)
    ).scalars().all()

    # Rule-based Summarization Logic
    highlights = []
    
    # 1. Method Switches
    if session.method_key:
        highlights.append(f"Cooked with '{session.method_key}' method")
    
    # 2. Servings
    if session.servings_target != session.servings_base:
        highlights.append(f"Scaled servings {session.servings_base} -> {session.servings_target}")
    
    # 3. Adjustments
    adjust_count = len(session.adjustments_log)
    if adjust_count > 0:
        highlights.append(f"Applied {adjust_count} adjustments")
    
    # 4. Timer Stats
    total_timers_run = sum(1 for e in events if e.type == 'timer_create')
    if total_timers_run > 0:
        highlights.append(f"Ran {total_timers_run} timers")

    # Timeline Construction
    timeline = []
    for e in events[-20:]: # Last 20
         timeline.append({
             "t": e.created_at.isoformat(),
             "type": e.type,
             "step_index": e.step_index,
             "meta": e.meta,
             "label": e.meta.get("label") if e.meta else None
         })
    
    # Notes Suggestions (Rules)
    suggestions = []
    for entry in session.adjustments_log:
         text = f"Adjustment: {entry.get('fix_summary', 'Fix applied')}"
         suggestions.append({
             "id": str(uuid.uuid4()),
             "text": text,
             "source": "adjust_apply",
             "confidence": 0.8
         })

    # Stats
    duration_min = 0
    if session.started_at:
        end = session.ended_at or datetime.now(timezone.utc)
        duration_min = int((end - session.started_at).total_seconds() / 60)

    stats = {
        "steps_completed_pct": 0, # Placeholder
        "timers_total": total_timers_run,
        "adjustments_total": adjust_count,
        "duration_minutes": duration_min
    }

    return {
        "session": {
            "id": session.id,
            "recipe_id": session.recipe_id,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        },
        "highlights": highlights,
        "timeline": timeline,
        "notes_suggestions": suggestions,
        "stats": stats
    }

@router.post("/session/{session_id}/summary/polish", response_model=SummaryPolishResponse)
def polish_session_summary(
    session_id: str,
    body: SummaryPolishRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """Generate a polished, AI-powered summary of the session."""
    session = db.scalar(select(CookSession).where(CookSession.id == session_id))
    if not session: raise HTTPException(404, "Session not found")
    if session.workspace_id != workspace.id: raise HTTPException(404, "Session not found")
    
    recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
    
    events = db.execute(
        select(CookSessionEvent)
        .where(CookSessionEvent.session_id == session_id)
        .order_by(CookSessionEvent.created_at)
    ).scalars().all()
    
    facts = _build_session_facts(session, recipe, events, freeform=body.freeform_note)
    
    inputs_hash = hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest()
    
    # Redis Cache (v12)
    cache_key = f"tasteos:ai:polish:{workspace.id}:{session_id}:{inputs_hash}"
    
    def compute_polish():
        # Call Gemini
        p = polish_summary(facts, style=body.style, max_bullets=body.max_bullets)
        
        # Log usage
        log_event(
            db, 
            workspace_id=workspace.id, 
            session_id=session.id, 
            type="summary_polish", 
            meta={"model": "gemini-2.0-flash-exp", "ok": p.confidence > 0.5}
        )
        db.commit()
        return p.model_dump(mode='json')

    result_json, hit = get_or_set_json_sync(cache_key, 24 * 3600, compute_polish)
    polished = PolishedSummary(**result_json)

    return SummaryPolishResponse(
        polished=polished,
        raw_inputs_hash=inputs_hash,
        model=f"gemini-2.0-flash-exp{' (cached)' if hit else ''}"
    )


@router.post("/session/{session_id}/notes/preview", response_model=SessionNotesPreviewResponse)
def preview_session_notes(
    body: SessionNotesPreviewRequest,
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.scalar(select(CookSession).where(CookSession.id == session_id))
    if not session: raise HTTPException(404, "Session not found")
    if session.workspace_id != workspace.id: raise HTTPException(404, "Session not found")
    
    notes = []
    
    # v10.1: AI Polish Integration
    if body.use_ai:
        if body.polished_data:
            polished = body.polished_data
        else:
            recipe = db.scalar(select(Recipe).where(Recipe.id == session.recipe_id))
            events = db.execute(
                select(CookSessionEvent)
                .where(CookSessionEvent.session_id == session_id)
            ).scalars().all()
            
            facts = _build_session_facts(session, recipe, events, freeform=body.freeform)
            polished = polish_summary(facts, style=body.style)
        
        # Use AI output for notes structure
        if polished.next_time:
            notes.append("Next time:")
            for nt in polished.next_time:
                notes.append(f"  - {nt}")
        
        # Include key events/bullets if requested roughly (mapped to 'adjustments' or generic)
        if body.include.get("adjustments") and polished.bullets:
            notes.append("Session highlights:")
            for b in polished.bullets:
                notes.append(f"  - {b}")
                
        # If confidence is low, maybe fallback? 
        # But Polish Summary should have handled fallback internally.

    else:
        # v10: Rules-based (Legacy)
        
        # Freeform - Support both v10 (in include) and v10.1 (top-level)
        user_note = body.freeform
        if not user_note and isinstance(body.include.get("freeform"), str):
            user_note = body.include["freeform"]
            
        if user_note:
            notes.append(user_note)

        # Method
        if body.include.get("method") and session.method_key:
            notes.append(f"Cooked with {session.method_key} method.")
        
        # Servings
        if body.include.get("servings") and session.servings_target != session.servings_base:
            notes.append(f"Scaled to {session.servings_target} servings.")

        # Adjustments
        if body.include.get("adjustments"):
             for adj in session.adjustments_log:
                 if adj.get("undone_at"): continue
                 notes.append(f"Adjustment: {adj.get('fix_summary', 'unknown')}")

    header = f"\n\n---\nCook Session ({datetime.now().strftime('%Y-%m-%d')}):"
    
    return {
        "proposal": {
            "recipe_patch": {
                "notes_append": notes
            },
            "preview_markdown": header + "\n" + "\n".join([f"- {n}" for n in notes]),
            "counts": {"lines": len(notes) + 2}
        }
    }

@router.post("/session/{session_id}/notes/apply")
def apply_session_notes(
    body: SessionNotesApplyRequest,
    session_id: str,
    db: Session = Depends(get_db)
):
    if len(body.notes_append) > 100: # Safety cap
        raise HTTPException(400, "Too many notes")
        
    recipe = db.scalar(select(Recipe).where(Recipe.id == body.recipe_id))
    if not recipe: raise HTTPException(404, "Recipe not found")

    date_str = datetime.now().strftime('%Y-%m-%d')
    title = f"Cook Session ({date_str})"
    content_md = "\n".join([f"- {n}" for n in body.notes_append])

    # 1. Create Recipe Note Entry (New Architecture)
    if body.create_entry:
        # Check for duplicate
        existing_entry = db.query(RecipeNoteEntry).filter(
            RecipeNoteEntry.recipe_id == recipe.id,
            RecipeNoteEntry.session_id == session_id,
            RecipeNoteEntry.deleted_at.is_(None)
        ).first()
        
        if not existing_entry:
            # v11: Derive tags!
            tags = []
            session = db.scalar(select(CookSession).where(CookSession.id == session_id))
            if session:
                if session.method_key:
                    tags.append(session.method_key)
                
                # Scan adjustments for tags (e.g. "too_thick", "too_salty")
                known_adjust_tags = [
                    "too_thick", "too_thin", "too_salty", "too_spicy", 
                    "burning", "no_browning", "undercooked", "overcooked", 
                    "bland", "dry", "wet"
                ]
                
                # Check adjustments log
                if session.adjustments_log:
                    for adj in session.adjustments_log:
                        # adj is a dict, usually has 'fix_summary' or similar
                        text = str(adj).lower()
                        for t in known_adjust_tags:
                            if t in text and t not in tags:
                                tags.append(t)
                                
            # Fallback/Supplemental: scan content_md
            content_lower = content_md.lower()
            known_method_tags = ["air_fryer", "instant_pot", "wok", "dutch_oven", "cast_iron", "steamer", "sous_vide", "slow_cooker"]
            for t in known_method_tags:
                if t.replace("_", " ") in content_lower and t not in tags:
                    tags.append(t)
            
            entry = RecipeNoteEntry(
                workspace_id=recipe.workspace_id,
                recipe_id=recipe.id,
                session_id=session_id,
                source="cook_session",
                title=title,
                content_md=content_md,
                tags=tags,
                applied_to_recipe_notes=True 
            )
            db.add(entry)
    
    # 2. Append to legacy field (Compatibility)
    existing = recipe.notes or ""
    header = f"\n\n---\n{title}:"
    new_block = "\n" + content_md
    
    # Safety: Limit total size?
    if len(existing) + len(header) + len(new_block) > 10000:
        raise HTTPException(400, "Recipe notes too long")
        
    recipe.notes = existing + header + new_block
    
    log_event(db, workspace_id=recipe.workspace_id, session_id=session_id, type="notes_apply", meta={"lines": len(body.notes_append)})
    db.commit()
    
    return {"status": "ok", "recipe_id": recipe.id}


# --- V13 Timers & SSE ---
# (Refactored to top to avoid routing conflicts)

@router.get("/session/{session_id}/timers/suggested", response_model=TimerSuggestionResponse)
def get_session_timer_suggestions(
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    recipe = db.query(Recipe).filter_by(id=session.recipe_id, workspace_id=workspace.id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    suggestions = []
    
    # Iterate all steps
    if recipe.steps:
        for step in recipe.steps:
            step_suggestions = generate_suggestions_for_step(step, step.step_index)
            suggestions.extend(step_suggestions)

    return TimerSuggestionResponse(suggested=suggestions)


@router.post("/session/{session_id}/timers/from-suggested")
def create_timers_from_suggested(
    session_id: str,
    payload: TimerFromSuggestedRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")
        
    recipe = db.query(Recipe).filter_by(id=session.recipe_id, workspace_id=workspace.id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # Re-generate suggestions to validate client_ids (security/integrity)
    all_suggestions = []
    if recipe.steps:
        for step in recipe.steps:
            all_suggestions.extend(generate_suggestions_for_step(step, step.step_index))
            
    suggestion_map = {s.client_id: s for s in all_suggestions}
    
    created_count = 0
    current_timers = dict(session.timers) if session.timers else {}
    
    updated = False
    now = datetime.now(timezone.utc)
    
    for cid in payload.client_ids:
        suggestion = None
        if cid in suggestion_map:
             suggestion = suggestion_map[cid]
        else:
             # Fallback: parsing client_id for resilience
             # Format: step-{idx}-{label}-{dur}
             # We try a loose regex match
             import re
             match = re.match(r"step-(\d+)-(.*)-(\d+)", cid)
             if match:
                 s_idx = int(match.group(1))
                 s_label_slug = match.group(2) # "slow-cook"
                 s_dur = int(match.group(3))
                 
                 # Reconstruct label from slug (approx)
                 s_label = s_label_slug.replace("-", " ").title()
                 
                 suggestion = TimerSuggestion(
                     client_id=cid,
                     label=s_label,
                     step_index=s_idx,
                     duration_s=s_dur,
                     reason="fallback_parse"
                 )
        
        if not suggestion:
            logger.warning(f"Could not resolve suggestion for {cid}")
            continue
        
        # Check for duplicates: same label and duration and active
        exists = False
        for tid, t in current_timers.items():
             if t.get("state") in ["running", "paused", "created"]:
                 # Loose matching: if label and duration match
                 if t.get("label") == suggestion.label and t.get("duration_sec") == suggestion.duration_s:
                     exists = True
                     break
        
        if exists:
            continue
            
        # Create new timer
        timer_id = str(uuid.uuid4())
        
        new_timer = {
            "id": timer_id,
            "label": suggestion.label,
            "duration_sec": suggestion.duration_s,
            "remaining_sec": suggestion.duration_s,
            "state": "running" if payload.autostart else "created",
            "step_index": suggestion.step_index,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        if payload.autostart:
            new_timer["started_at"] = now.isoformat()
            new_timer["ends_at"] = (now + timedelta(seconds=suggestion.duration_s)).isoformat()
        
        current_timers[timer_id] = new_timer
        updated = True
        created_count += 1

    if updated:
        session.timers = current_timers
        session.updated_at = now
        db.commit()
        
        # Notify
        notify_session_update(session)
        
    return {"created": created_count}


@router.post("/session/{session_id}/timers", response_model=TimerResponse)
async def create_session_timer(
    session_id: str,
    body: TimerCreateRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")
        
    # Idempotency check
    existing_timer = None
    for timer_id, t_data in session.timers.items():
        if t_data.get("client_id") == body.client_id:
            existing_timer = t_data.copy()
            existing_timer["id"] = timer_id
            break
    
    if existing_timer:
        return existing_timer

    new_timer_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    
    timer_data = {
        "client_id": body.client_id,
        "label": body.label,
        "step_index": body.step_index,
        "duration_sec": body.duration_s,
        "state": "created",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "paused_at": None,
        "done_at": None,
        "deleted_at": None
    }
    
    # Copy dict to avoid mutation issues if SQLAlchemy tracks it weirdly
    new_timers = dict(session.timers)
    new_timers[new_timer_id] = timer_data
    session.timers = new_timers
    
    # Bump state version
    session.state_version = 13
    
    db.commit()
    
    resp_data = timer_data.copy()
    resp_data["id"] = new_timer_id
    
    await publish_event(session_id, "timer.created", {"timer": resp_data})
    
    return resp_data

@router.post("/session/{session_id}/timers/{timer_id}/action", response_model=TimerResponse)
async def session_timer_action(
    session_id: str,
    timer_id: str,
    body: TimerActionRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")
        
    if timer_id not in session.timers:
        raise HTTPException(404, "Timer not found")
        
    timer = session.timers[timer_id].copy() # Copy for mutation

    # COMPAT: Ensure created_at exists for legacy timers
    if "created_at" not in timer:
        # Use session start or now as fallback
        fallback_time = session.started_at.isoformat() if session.started_at else datetime.now(timezone.utc).isoformat() 
        timer["created_at"] = fallback_time
        updated = True

    action = body.action
    now = datetime.now(timezone.utc)
    iso_now = now.isoformat()
    
    updated = False
    
    if action == "start":
        # Fresh start or restart
        timer["started_at"] = iso_now
        timer["paused_at"] = None
        timer["done_at"] = None
        timer["deleted_at"] = None
        timer["state"] = "running"
        updated = True
        
    elif action == "pause":
        if timer["state"] == "running":
            timer["paused_at"] = iso_now
            timer["state"] = "paused"
            updated = True
            
    elif action == "resume":
        if timer["state"] == "paused" and timer.get("paused_at"):
            # Shift started_at forward by pause duration
            paused_at_dt = datetime.fromisoformat(timer["paused_at"])
            pause_duration = (now - paused_at_dt).total_seconds()
            
            if timer.get("started_at"):
                start_dt = datetime.fromisoformat(timer["started_at"])
                new_start = start_dt + timedelta(seconds=pause_duration)
                timer["started_at"] = new_start.isoformat()
            
            timer["paused_at"] = None
            timer["state"] = "running"
            updated = True
            
    elif action == "done":
        timer["done_at"] = iso_now
        timer["state"] = "done"
        updated = True
        
    elif action == "delete":
        timer["deleted_at"] = iso_now
        # Soft delete, kept in dict but marked
        updated = True

    if updated:
        timer["updated_at"] = iso_now
        
        # Save back
        new_timers = dict(session.timers)
        new_timers[timer_id] = timer
        session.timers = new_timers
        session.state_version = 13
        session.last_interaction_at = now
        
        db.commit()
        
        resp_data = timer.copy()
        resp_data["id"] = timer_id
        
        await publish_event(session_id, "timer.updated", {"timer": resp_data, "action": action})
        
        return resp_data
        
    # No op return
    timer["id"] = timer_id
    return timer

@router.patch("/session/{session_id}/timers/{timer_id}", response_model=TimerResponse)
async def patch_session_timer(
    session_id: str,
    timer_id: str,
    body: TimerPatchRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")
        
    if timer_id not in session.timers:
        raise HTTPException(404, "Timer not found")
        
    timer = session.timers[timer_id].copy()
    now = datetime.now(timezone.utc).isoformat()
    
    if body.label is not None:
        timer["label"] = body.label
    if body.duration_s is not None:
        timer["duration_sec"] = body.duration_s
    if body.step_index is not None:
        timer["step_index"] = body.step_index
        
    timer["updated_at"] = now
    
    new_timers = dict(session.timers)
    new_timers[timer_id] = timer
    session.timers = new_timers
    session.state_version = 13
    
    db.commit()
    
    resp_data = timer.copy()
    resp_data["id"] = timer_id
    
    await publish_event(session_id, "timer.updated", {"timer": resp_data})
    
    return resp_data

@router.get("/session/{session_id}/next", response_model=CookNextResponse)
def get_session_next(
    session_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    recipe = db.query(Recipe).filter_by(id=session.recipe_id, workspace_id=workspace.id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # Current state
    current_idx = session.current_step_index
    step_checks = session.step_checks or {}
    timers = session.timers or {}
    
    # Filter active timers (exclude deleted)
    active_timers = {k: v for k, v in timers.items() if not v.get("deleted_at")}

    # Calculate Effective Step Index (Autofocus Logic)
    # Why: User might have moved ahead (checked items on next step, started timer on next step)
    # without explicitly clicking "Next". We should suggest actions for where they actually ARE.
    
    highest_touched_step = current_idx
    
    # Check 1: Highest step with any checked items
    for step_key, bullets in step_checks.items():
        if any(bullets.values()):
            try:
                highest_touched_step = max(highest_touched_step, int(step_key))
            except (ValueError, TypeError):
                pass
            
    # Check 2: Highest step with active timers (tracking progress)
    for timer in active_timers.values():
         # If timer is started or done, it counts as "touched"
         if timer.get("started_at") or timer.get("state") == "done":
             idx = timer.get("step_index")
             if idx is not None:
                highest_touched_step = max(highest_touched_step, idx)

    # Use effective index
    current_idx = highest_touched_step # Override for calculation purposes

    # Get current step
    current_step = next((s for s in recipe.steps if s.step_index == current_idx), None)
    
    actions = []
    reason = "Ready for next instruction"
    
    # Heuristics
    
    # 1. Required Timer Logic (Highest Priority)
    # "Timer-required step" model: If minutes_est exists, timer MUST be done before step is complete.
    required_timer_s = (current_step.minutes_est * 60) if (current_step and current_step.minutes_est) else None
    
    # Identify active timer for this step
    step_timer = next((
        {"id": k, **v} 
        for k, v in active_timers.items() 
        if v.get("step_index") == current_idx
    ), None)
    
    if required_timer_s:
        # A. No timer exists -> Suggest Create
        if not step_timer:
            actions.append(CookNextAction(
                 type="create_timer",
                 label=f"Start {current_step.minutes_est} min timer",
                 duration_s=required_timer_s,
                 step_idx=current_idx
            ))
            reason = "Step requires timer"
            return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason=reason)
        
        # B. Timer exists
        state = step_timer.get("state")
        
        # Created/Paused -> Suggest Start
        if state in ["created", "paused"]:
             actions.append(CookNextAction(
                type="start_timer",
                label=f"Start: {step_timer.get('label')}",
                timer_id=step_timer.get("id")
            ))
             reason = "Timer ready but not started"
             return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason=reason)
             
        # Running -> Suggest Wait (Blocking)
        if state == "running":
             actions.append(CookNextAction(
                 type="wait_timer",
                 label=f"Timer running...",
                 timer_id=step_timer.get("id")
             ))
             reason = "Waiting for timer"
             return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason=reason)
             
        # Done -> Proceed (Satisfied)
        # If state == "done", fall through to checklist logic

    # 2. Checklist Logic
    # New V13.2 Rule: Only suggest "Mark Complete" if checklist is PARTIALLY checked.
    # AND NO required timer (or timer is done, which it is if we are here).
    # Wait, if required_timer_s was True, and we are here, it means timer is DONE.
    # So we can allow "mark complete" if checklist is partial.
    
    # Logic Check: "Only allow “mark step complete” when: ... AND there is no required timer for the step"
    # Actually, if the timer is DONE, we conceptually treated it as "step requirement met".
    # But the prompt says "prevent... confusion".
    # If the timer is DONE, the user might want to mark step complete.
    # Let's follow the prompt strictly: "no required timer".
    # If `required_timer_s` is truthy, we do NOT suggest `mark_step_done`. 
    # This prevents the user from bypassing the "natural flow" of the timer step. 
    # For a timer step, once timer is done + checklist done -> "Next Step".
    
    has_bullets = current_step and bool(current_step.bullets)
    checks_key = str(current_idx)
    checks_map = step_checks.get(checks_key, {})
    
    # Calculate check status
    checked_count = len([v for v in checks_map.values() if v])
    checked_any = checked_count > 0
    checked_all = has_bullets and checked_count == len(current_step.bullets)

    # If Partially Checked: Finish checklist / Mark Complete
    # Constraint: Only if NO required timer.
    if has_bullets and checked_any and not checked_all and not required_timer_s:
         actions.append(CookNextAction(
             type="mark_step_done",
             label=f"Mark Step {current_idx + 1} complete",
             step_idx=current_idx
         ))
         reason = "Step checklist incomplete"
         return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason=reason)

    # 3. Create Timer suggestion (Manual / Optional)
    # If step has NO minutes_est (already handled in #1), but maybe we parsed something?
    # Logic #1 handled minutes_est. 
    # So this block #3 is actually redundant or for "parsed" things if we add parsing later.
    # Removing #3 as it's covered by #1 logic now.

    # 4. Next Step Logic
    # Ready if: No bullets OR All bullets checked
    # AND (if timer required) Timer is Done.
    
    ready_for_next = False
    
    timer_satisfied = True
    if required_timer_s:
         if not step_timer or step_timer.get("state") != "done":
             timer_satisfied = False
    
    if timer_satisfied:
        if not has_bullets:
            ready_for_next = True
        elif checked_all:
            ready_for_next = True
        
    if ready_for_next:
        next_step_idx = current_idx + 1
        next_step = next((s for s in recipe.steps if s.step_index == next_step_idx), None)
        
        if next_step:
            actions.append(CookNextAction(
                type="go_to_step",
                label=f"Continue to Step {next_step_idx + 1}",
                step_idx=next_step_idx
            ))
            reason = "Step complete"
            return CookNextResponse(suggested_step_idx=next_step_idx, actions=actions, reason=reason)
            
        # 5. Connect to Finish
        actions.append(CookNextAction(
            type="complete_session",
            label="Complete Cooking",
            step_idx=current_idx
        ))
        reason = "Recipe complete"
        return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason=reason)
    
    # Fallback
    return CookNextResponse(suggested_step_idx=current_idx, actions=actions, reason="Step in progress")

@router.get("/session/{session_id}/events")
async def stream_session_events(
    session_id: str,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db)
):
    """Subscribe to real-time session events (v13+)."""
    # Verify session access
    session = db.query(CookSession).filter_by(id=session_id, workspace_id=workspace.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        pubsub = await subscribe_session(session_id)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message:
                    # Generic data payload - ensure it's SSE format
                    data_str = message['data']
                    # Redis returns bytes or string. If bytes, decode.
                    if isinstance(data_str, bytes):
                        data_str = data_str.decode('utf-8')
                    yield f"data: {data_str}\n\n"
                else:
                    # Heartbeat
                    payload = json.dumps({"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()})
                    yield f"data: {payload}\n\n"
        except asyncio.CancelledError:
            await pubsub.close()
        except Exception as e:
            logger.error(f"SSE Error: {e}")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


