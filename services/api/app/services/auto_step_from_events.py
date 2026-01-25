from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models import CookSession, CookSessionEvent
import math

def calculate_auto_step_from_events(session: CookSession, db: Session, now=None):
    """
    Analyzes recent session events to determine the suggested step index.
    Updates the session with the new suggestion if applicable.
    """
    if not now:
        now = datetime.now(timezone.utc)

    # 1. Manual Override Check
    # If a manual navigation happened recently, we respect it and do NOT auto-jump.
    # We still compute the suggestion, but cap confidence.
    in_override_window = False
    if session.manual_override_until:
        # Ensure aware comparison
        override_until = session.manual_override_until
        if override_until.tzinfo is None:
            override_until = override_until.replace(tzinfo=timezone.utc)
            
        if now < override_until:
            in_override_window = True

    # 2. Fetch Recent Events (Last 15 minutes is usually enough context)
    cutoff = now - timedelta(minutes=15)
    stmt = (
        select(CookSessionEvent)
        .where(
            CookSessionEvent.session_id == session.id,
            CookSessionEvent.created_at >= cutoff
        )
        .order_by(desc(CookSessionEvent.created_at))
        .limit(200)
    )
    events = db.execute(stmt).scalars().all()

    # 3. Score Steps
    # We'll accumulate scores for each step index based on event types and recency
    step_scores = {}
    
    # Initialize with 0 for all reasonable steps (e.g. up to current + a few)
    # Actually, dynamic dict is fine.

    for event in events:
        # Age in minutes
        evt_time = event.created_at
        if evt_time.tzinfo is None:
            evt_time = evt_time.replace(tzinfo=timezone.utc)
        
        age_min = (now - evt_time).total_seconds() / 60.0
        if age_min < 0: age_min = 0

        # Decay factor: recent events matter much more.
        # exp(-age/6) => 6 mins ago = 0.36 weight, 0 mins = 1.0 weight
        weight = math.exp(-age_min / 6.0)
        
        step_idx = event.step_index
        
        # If event has no specific step (like global pause), skip step scoring
        if step_idx is None:
            continue
            
        points = 0.0
        
        if event.type == "timer_start":
            points = 6.0
        elif event.type == "timer_done":
            points = 3.0
        elif event.type == "timer_create":
            points = 2.0
        elif event.type == "check_step": # check toggle
            points = 2.0
        elif event.type == "servings_change" or event.type == "adjust_apply":
            points = 4.0
        elif event.type == "step_navigate":
            # Navigation is a strong signal of intent
            points = 3.0
        
        if points > 0:
            current = step_scores.get(step_idx, 0.0)
            step_scores[step_idx] = current + (points * weight)

    # 4. Determine Suggestion
    if not step_scores:
        # No signal, stay put.
        # If we want to clear suggestion, we can:
        # session.auto_step_suggested_index = None # Or keep last known?
        # Usually easier to keep null if no recent signal.
        return

    # Find Top 2
    sorted_steps = sorted(step_scores.items(), key=lambda x: x[1], reverse=True)
    best_step, best_score = sorted_steps[0]
    
    second_score = 0.0
    if len(sorted_steps) > 1:
        second_score = sorted_steps[1][1]

    # Calculate Confidence
    # Ratio of best against noise
    # Base formula: score / (score + noise + 1)
    # The +1 prevents div by zero and sets a baseline threshold
    raw_confidence = best_score / (best_score + second_score + 1.0)
    
    # Clamp to reasonable range
    confidence = max(0.35, min(0.95, raw_confidence))
    
    if in_override_window:
        confidence = min(confidence, 0.55)

    # Update Session
    session.auto_step_suggested_index = best_step
    session.auto_step_confidence = confidence
    
    # Simple reason string (highest contributing recent event type on that step)
    # Find the most recent event for the best step to cite as "reason"
    reason_event = next((e for e in events if e.step_index == best_step), None)
    if reason_event:
        pretty_names = {
            "timer_start": "Timer started",
            "timer_done": "Timer finished",
            "check_step": "Item checked",
            "step_navigate": "Navigated here",
            "timer_create": "Timer created"
        }
        session.auto_step_reason = pretty_names.get(reason_event.type, "Recent activity")

    # 5. Auto-Jump Logic
    # Only if configured to auto-jump AND confident AND not in override
    if (session.auto_step_enabled and 
        session.auto_step_mode == 'auto_jump' and 
        not in_override_window and 
        confidence >= 0.80 and
        best_step != session.current_step_index):
        
        session.current_step_index = best_step
        # Note: We should probably log this system usage, but for now we just move.
