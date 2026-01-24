"""FastAPI dependencies for TasteOS API.

Provides:
- Database session dependency
- Workspace resolution (header → env → fallback)
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Workspace
from .settings import settings


def get_workspace(
    db: Session = Depends(get_db),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> Workspace:
    """Resolve workspace via header, env, or fallback.
    
    Resolution order:
    1. X-Workspace-Id header (if present):
       - Try as UUID
       - Try as slug
       - If not found -> 404 (Strict validation)
       
    2. settings.default_workspace_slug env var
    3. First workspace in DB
    
    Returns:
        Workspace object
        
    Raises:
        HTTPException 404 if no workspace found or header is invalid
    """
    workspace: Optional[Workspace] = None
    
    # 1. Try header (Strict)
    if x_workspace_id:
        # Check if it looks like a UUID
        try:
            import uuid
            uuid_obj = uuid.UUID(x_workspace_id)
            workspace = db.get(Workspace, str(uuid_obj))
        except ValueError:
            # Not a UUID, try as slug
            workspace = db.query(Workspace).filter(Workspace.slug == x_workspace_id).first()
            
        if workspace:
            return workspace
            
        # If header was provided but no workspace found, we MUST 404
        # to prevent accidental fallback to "default" when user meant "specific"
        raise HTTPException(
            status_code=404,
            detail=f"Workspace '{x_workspace_id}' not found"
        )
    
    # 2. Try default slug from settings
    if settings.default_workspace_slug:
        workspace = db.query(Workspace).filter(
            Workspace.slug == settings.default_workspace_slug
        ).first()
        if workspace:
            return workspace
    
    # 3. Fallback to first workspace
    workspace = db.query(Workspace).order_by(Workspace.created_at).first()
    if workspace:
        return workspace
    
    raise HTTPException(
        status_code=404,
        detail="No workspace found. Run POST /api/dev/seed to create one."
    )


def get_workspace_optional(
    db: Session = Depends(get_db),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> Optional[Workspace]:
    """Like get_workspace but returns None instead of raising."""
    try:
        return get_workspace(db=db, x_workspace_id=x_workspace_id)
    except HTTPException:
        return None
