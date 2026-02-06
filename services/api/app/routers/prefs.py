"""
Router for workspace preferences.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from ..models import Workspace
from ..schemas import UnitPrefs, UnitPrefsUpdate, UserPrefsResponse
from ..deps import get_db, get_workspace

router = APIRouter()

DEFAULT_UNIT_PREFS = UnitPrefs().model_dump()

def merge_prefs(base: dict, update: dict) -> dict:
    """Deep merge implementation if needed, but for now shallow merge of top keys is fine."""
    # Since our prefs structure is shallow (lists are atomic replacements usually), shallow update is okay.
    # But let's be careful.
    merged = base.copy()
    for k, v in update.items():
        if v is not None:
             merged[k] = v
    return merged

@router.get("/prefs/unit", response_model=UserPrefsResponse)
def get_unit_prefs(
    workspace: Workspace = Depends(get_workspace),
):
    """Get current unit preferences for the workspace."""
    # Merge stored prefs with defaults to ensure new keys appear
    stored = workspace.unit_prefs_json or {}
    merged = DEFAULT_UNIT_PREFS.copy()
    merged.update(stored)
    
    return UserPrefsResponse(unit_prefs=UnitPrefs(**merged))

@router.patch("/prefs/unit", response_model=UserPrefsResponse)
def update_unit_prefs(
    update: UnitPrefsUpdate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace),
):
    """Update unit preferences."""
    current = workspace.unit_prefs_json or {}
    # Apply updates
    updates_dict = update.model_dump(exclude_unset=True)
    
    # Merge
    merged = current.copy()
    merged.update(updates_dict)
    
    # Sanitize against schema defaults to keep DB clean? 
    # Or just save what we have. Saving full object is safer for specific overrides.
    
    workspace.unit_prefs_json = merged
    db.commit()
    db.refresh(workspace)
    
    # Re-merge with system defaults for response
    final_merged = DEFAULT_UNIT_PREFS.copy()
    final_merged.update(workspace.unit_prefs_json)
    
    return UserPrefsResponse(unit_prefs=UnitPrefs(**final_merged))
