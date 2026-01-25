from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import CookSession, RecipeStep

def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def calculate_auto_step(session: CookSession, db: Session, now: datetime) -> None:
    """
    Calculates the suggested step based on heuristics and updates the session object in-place.
    """
    if not session.auto_step_enabled:
        return

    # Normalize datetimes for comparison (SQLite compat)
    now = ensure_aware(now)
    last_interaction = ensure_aware(session.last_interaction_at)
    manual_until = ensure_aware(session.manual_override_until)

    # Heuristics
    suggestion = None
    confidence = 0.0
    reason = None
    
    # Priority 1: Timer running (Strongest signal)
    running_timer_step = None
    for timer in session.timers.values():
        if timer.get("state") == "running":
            running_timer_step = timer.get("step_index")
            break
            
    if running_timer_step is not None:
        suggestion = running_timer_step
        confidence = 0.80
        reason = "Timer running"
    
    # Priority 2: Step completion
    if suggestion is None:
        current_idx = session.current_step_index
        step_key = str(current_idx)
        checks = session.step_checks.get(step_key, {})
        checked_count = sum(1 for v in checks.values() if v)
        
        if checked_count > 0:
            # Fetch total bullets for this step
            step_record = db.scalar(
                select(RecipeStep)
                .where(RecipeStep.recipe_id == session.recipe_id, RecipeStep.step_index == current_idx)
            )
            
            if step_record and step_record.bullets and len(step_record.bullets) > 0:
                percentage = checked_count / len(step_record.bullets)
                if percentage >= 0.8:
                    # Suggest next step if it exists
                    next_step = db.scalar(
                         select(RecipeStep.id)
                         .where(RecipeStep.recipe_id == session.recipe_id, RecipeStep.step_index == current_idx + 1)
                    )
                    if next_step:
                        suggestion = current_idx + 1
                        confidence = 0.70
                        reason = "Step mostly complete"

    # Priority 3: Recent interaction (< 10 mins)
    # Only suggest if it's different from current step (otherwise fallback covers it)
    if suggestion is None and last_interaction and last_interaction > now - timedelta(minutes=10) and session.last_interaction_step_index is not None:
         if session.last_interaction_step_index != session.current_step_index:
             suggestion = session.last_interaction_step_index
             confidence = 0.75
             reason = "Recent interaction"

    # Fallback
    if suggestion is None:
        suggestion = session.current_step_index
        confidence = 0.40
        reason = "Current step"

    # Apply Manual Override Cap
    if manual_until and manual_until > now:
        # If override is active, cap confidence to prevent auto-jump
        if confidence > 0.4:
            confidence = 0.4
        reason = "Manual override active"

    # Update session
    session.auto_step_suggested_index = suggestion
    session.auto_step_confidence = confidence
    session.auto_step_reason = reason
    
    # Auto-jump logic
    if session.auto_step_mode == "auto_jump" and confidence >= 0.75:
        if session.current_step_index != suggestion:
             session.current_step_index = suggestion
