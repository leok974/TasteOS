from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from ..deps import get_db, get_workspace
from ..models import Workspace, IngredientDensityOverride
from ..schemas import IngredientDensityOut, IngredientDensityUpsert, IngredientDensityListResponse
from ..services.ingredient_normalize import normalize_ingredient_key
from ..services.unit_conversion import get_unit_info, normalize_unit, calculate_density_factor

router = APIRouter()

@router.get("/densities", response_model=IngredientDensityListResponse)
def list_densities(
    query: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    stmt = select(IngredientDensityOverride).where(
        IngredientDensityOverride.workspace_id == workspace.id
    )
    
    if query:
        norm_q = normalize_ingredient_key(query)
        # Search by key or display name partial match
        stmt = stmt.where(
            (IngredientDensityOverride.ingredient_key.contains(norm_q)) |
            (IngredientDensityOverride.display_name.ilike(f"%{query}%"))
        )
        
    stmt = stmt.limit(limit)
    item_rows = db.execute(stmt).scalars().all()
    
    return {"items": item_rows}

@router.put("/densities", response_model=IngredientDensityOut)
def upsert_density(
    req: IngredientDensityUpsert,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    # 1. Normalize
    key = normalize_ingredient_key(req.ingredient_name)
    if not key:
        raise HTTPException(status_code=400, detail="Invalid ingredient name")
    
    # 2. Convert user input to g/ml using helper
    g_per_ml = calculate_density_factor(
        req.density.mass_value, req.density.mass_unit,
        req.density.vol_value, req.density.vol_unit
    )
    
    if g_per_ml is None:
         raise HTTPException(status_code=400, detail="Invalid units (must be one mass and one volume unit)")
    
    # Validate sane range (0.05 to 5.0)
    # Water = 1.0.  Lead = 11.0.  Balsa wood = 0.16.  Aerogel = 0.00something.
    # Flour ~ 0.5-0.6. Sugar ~ 0.8. Salt ~ 1.2.
    if not (0.05 <= g_per_ml <= 5.0):
        # Allow forceful override via a query param in future if needed, but for now block insane values
        raise HTTPException(status_code=400, detail="Density out of sane range (0.05 - 5.0 g/ml)")

    # 3. Check existing
    existing = db.execute(
        select(IngredientDensityOverride).where(
            IngredientDensityOverride.workspace_id == workspace.id,
            IngredientDensityOverride.ingredient_key == key
        )
    ).scalar_one_or_none()
    
    if existing:
        existing.display_name = req.ingredient_name
        existing.density_g_per_ml = g_per_ml
        existing.source = "user"
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_override = IngredientDensityOverride(
            workspace_id=workspace.id,
            ingredient_key=key,
            display_name=req.ingredient_name,
            density_g_per_ml=g_per_ml,
            source="user"
        )
        db.add(new_override)
        db.commit()
        db.refresh(new_override)
        return new_override

@router.delete("/densities/{id}")
def delete_density(
    id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_workspace)
):
    existing = db.execute(
        select(IngredientDensityOverride).where(
            IngredientDensityOverride.id == id,
            IngredientDensityOverride.workspace_id == workspace.id
        )
    ).scalar_one_or_none()
    
    if not existing:
         raise HTTPException(404, "Density override not found")
         
    db.delete(existing)
    db.commit()
    return {"ok": True}
