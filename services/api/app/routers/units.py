"""
Router for unit conversion utilities.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..deps import get_db, get_workspace
from ..schemas import UnitConvertRequest, UnitConvertResponse, UnitPrefs
from ..services.unit_conversion import convert_unit, auto_select_unit
from ..services.ingredient_normalize import normalize_ingredient_key
from ..models import Workspace, IngredientDensityOverride
from .prefs import DEFAULT_UNIT_PREFS

router = APIRouter()

@router.post("/convert", response_model=UnitConvertResponse)
def convert_units(
    req: UnitConvertRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    """
    Convert a quantity from one unit to another.
    """
    # 1. Resolve Prefs
    prefs_dict = DEFAULT_UNIT_PREFS.copy()
    if workspace.unit_prefs_json:
        prefs_dict.update(workspace.unit_prefs_json)
    prefs = UnitPrefs(**prefs_dict)

    # 2. Resolve Target Unit
    to_unit = req.to_unit
    if not to_unit:
        # Determine system: Request Override > Workspace Prefs > Default
        # Check UnitPrefs schema if 'preferred_system' or 'system' is the field.
        # Looking at schema from context, it's 'system' in UnitPrefs (default "us")
        system = req.target_system or prefs.system
        
        # Auto-select based on system preference
        to_unit = auto_select_unit(
            qty=req.qty, 
            current_unit=req.from_unit, 
            target_system=system
        )
    
    # 3. Resolve Cross-Type Permission
    allow_cross = req.force_cross_type
    if allow_cross is None:
        allow_cross = prefs.allow_cross_type
        
    # 4. Resolve Density Override
    override_val = None
    if req.ingredient_name:
         key = normalize_ingredient_key(req.ingredient_name)
         # Find workspace override
         override = db.execute(
             select(IngredientDensityOverride).where(
                 IngredientDensityOverride.workspace_id == workspace.id,
                 IngredientDensityOverride.ingredient_key == key
             )
         ).scalar_one_or_none()
         
         if override:
             override_val = float(override.density_g_per_ml)
         
         # Policy Check: if "known_only" and no override, forbid generic density?
         # The prompt says: if known_only -> 400.
         # But generic density is handled inside `convert_unit` currently.
         # To strictly enforce "known_only", we need to know if `convert_unit` used generic.
         # `convert_unit` returns confidence.
         
    # 5. Perform Conversion
    result = convert_unit(
        qty=req.qty,
        from_unit=req.from_unit,
        to_unit=to_unit,
        ingredient_name=req.ingredient_name or "",
        allow_cross_type=allow_cross or False,
        override_density=override_val
    )
    
    # 4.1 Post-Conversion Policy Check
    if req.ingredient_name and prefs.density_policy == "known_only":
        # If result was successful but confidence isn't high, it essentially used common table or failed.
        # But if override_val was provided, confidence is high.
        # If no override_val, and logic used generic density -> confidence is "medium" or "low".
        # So if known_only is true, we must have high confidence (override) for cross-type.
        
        # Checking result.confidence:
        # "high" -> override or same-unit
        # "medium" -> generic density
        # "low"/"none" -> failed
        
        # How do we know if it was a cross-type conversion?
        # `convert_unit` handles logic internally. 
        # If we passed override_density, it returns high.
        # If we didn't, and it used generic, it uses "medium" (actually I set it to that in previous step? Or did I?)
        # Looking at `convert_unit`:
        # Generic density -> confidence "low" (generic match) or density from estimate_density.
        # Wait, `estimate_density` returns "medium" for exact string matches in generic table?
        # Let's assume generic table returns < "high". 
        
        # Actually simplest check:
        # If conversion worked (qty > 0) AND confidence != "high" AND same unit type check?
        # The prompt says: "without override + known_only -> 400"
        
        # Refined Logic:
        # If no override found AND strict policy?
        # But maybe same-unit conversion doesn't need density.
        # So we should only block CROSS-TYPE conversions that lack override.
        
        # We can detect cross-type by checking result note or just comparing unit types here.
        # But `convert_unit` abstracts unit types.
        pass # Optimization for v14.3 or strict implementation later. 
             # For now, let's stick to "override takes precedence".
             # If "known_only" policy is strictly required now:
             # "if density_policy='known_only' -> 400 error ... Cross-type conversion requires a density"
             
             # I need to know if it WAS cross type.
             # I can check `result.is_approx`.
             # If `is_approx` is True, it implies density was used (cross-type) AND it wasn't an override (override sets is_approx=False).
             
    if prefs.density_policy == "known_only" and result.is_approx:
         raise HTTPException(
             status_code=400, 
             detail=f"Cross-type conversion requires a density override for '{req.ingredient_name}' (Strict Mode)"
         )

    return UnitConvertResponse(
        qty=result.qty,
        unit=result.unit,
        confidence=result.confidence, # type: ignore
        note=result.note,
        is_approx=result.is_approx
    )

