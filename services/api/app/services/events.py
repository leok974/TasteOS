from typing import Any, Optional
import json
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from ..models import CookSessionEvent

logger = logging.getLogger("tasteos.events")

MAX_META_SIZE = 4096  # 4KB safety limit

def log_event(
    db: Session,
    *,
    workspace_id: str,
    session_id: str,
    type: str,
    step_index: Optional[int] = None,
    bullet_index: Optional[int] = None,
    timer_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None
) -> None:
    """Log a cook session event to the database.
    
    Args:
        db: Database session
        workspace_id: Workspace context owner
        session_id: Cook session ID
        type: Event type (session_start, step_nav, check_toggle, etc.)
        step_index: Optional step context
        bullet_index: Optional bullet context
        timer_id: Optional timer ID context
        meta: Optional JSON metadata. Will be sanitized and truncated if too large.
    """
    safe_meta = meta or {}
    
    # Simple JSON size guard
    # In a real app we might want to be smarter about trimming specific fields
    try:
        json_str = json.dumps(safe_meta)
        if len(json_str) > MAX_META_SIZE:
            logger.warning(f"Event meta too large ({len(json_str)} bytes), truncating.")
            safe_meta = {"_error": "payload_too_large", "_original_keys": list(safe_meta.keys())}
    except Exception as e:
        logger.error(f"Failed to serialize event meta: {e}")
        safe_meta = {"_error": "serialization_failed"}

    event = CookSessionEvent(
        workspace_id=workspace_id,
        session_id=session_id,
        type=type,
        step_index=step_index,
        bullet_index=bullet_index,
        timer_id=timer_id,
        meta=safe_meta,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(event)
    # We don't commit here to allow the caller to wrap potentially in a transaction 
    # or commit alongside the main operation. 
    # However, if we want events even if the main operation fails (unlikely given SQLAlchemy transaction model),
    # we would need a separate session. For now, assuming standard transactional integrity is desired.
