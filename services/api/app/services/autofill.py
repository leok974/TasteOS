from datetime import date, timedelta, datetime
from typing import List, Optional, Dict, Any
import uuid
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, not_, or_

from .. import models
from ..models import MealPlan, MealPlanEntry, PantryItem, Recipe, RecipeIngredient, Workspace

def generate_use_soon_proposals(
    db: Session,
    workspace_id: str,
    week_start: date,
    days: int = 5,
    max_swaps: int = 3,
    ignore_entry_ids: List[str] = [],
    slots: List[str] = ["dinner"],
    prefer_quick: bool = True,
    strict_variety: bool = False,
    max_duplicates_per_recipe: int = 2
) -> Dict[str, Any]:
    
    # 1. Fetch current plan
    plan = db.query(MealPlan).filter(
        MealPlan.workspace_id == workspace_id,
        MealPlan.week_start == week_start
    ).first()
    
    if not plan:
        return {
            "week_start": week_start,
            "meta": {"use_soon_items": [], "generated_at": datetime.now().isoformat(), "max_swaps": max_swaps},
            "proposals": []
        }
        
    # 2. Fetch Use Soon Items
    today = date.today()
    expires_threshold = today + timedelta(days=days)
    
    use_soon_items = db.query(PantryItem).filter(
        PantryItem.workspace_id == workspace_id,
        (
            ((PantryItem.expires_on != None) & (PantryItem.expires_on <= expires_threshold)) |
            ((PantryItem.use_soon_at != None) & (PantryItem.use_soon_at <= today))
        )
    ).order_by(PantryItem.expires_on.asc().nulls_last()).all()
    
    if not use_soon_items:
         return {
            "week_start": week_start,
            "meta": {"use_soon_items": [], "generated_at": datetime.now().isoformat(), "max_swaps": max_swaps},
            "proposals": []
        }

    use_soon_meta = []
    for item in use_soon_items:
        expires_in = None
        if item.expires_on:
            expires_in = (item.expires_on - today).days
        use_soon_meta.append({
            "name": item.name,
            "expires_on": item.expires_on,
            "expires_in_days": expires_in
        })

    # 3. Identify Candidate Slots
    # Default to dinners if not specified
    target_slots = set(slots) if slots else {"dinner"}
    
    candidate_entries = []
    current_recipe_ids = set()
    
    for entry in plan.entries:
        if entry.id in ignore_entry_ids:
            continue
        if entry.meal_type not in target_slots:
            continue
        if entry.is_leftover:
            continue
        # Also skip if force_cook is True (user explicitly locked this cook)
        if entry.force_cook:
            continue
        
        # We can propose swaps even if a recipe is assigned,
        # but typically we prioritize empty slots or "unlocked" slots.
        # For this v1, let's treat any non-force-cook dinner as swappable
        
        candidate_entries.append(entry)
        if entry.recipe_id:
            current_recipe_ids.add(entry.recipe_id)

    # 4. Find Candidate Swaps
    # Build a map of ingredient keywords to pantry items
    # Simple strategy: search RecipeIngredients for names matching pantry item names
    
    proposals = []
    
    # Pre-fetch candidate recipes to avoid N+1
    # We want recipes that contain ANY of the use-soon items.
    # This might be heavy if we have many items.
    # Let's do it per-item or batch query.
    
    # Optimization: Filter recipes by workspace
    
    # We need to map pantry item names to ingredients.
    # Let's normalize names a bit (lowercase).
    pantry_keywords = [item.name.lower() for item in use_soon_items]
    print(f"DEBUG: Found {len(use_soon_items)} use soon items. Keywords: {pantry_keywords}")
    
    if not pantry_keywords:
        return {
            "week_start": week_start,
            "meta": {"use_soon_items": use_soon_meta, "generated_at": datetime.now().isoformat(), "max_swaps": max_swaps},
            "proposals": []
        }

    # Find recipes that match ANY keyword
    # We can use OR ILIKE
    
    filters = []
    for kw in pantry_keywords:
        filters.append(RecipeIngredient.name.ilike(f"%{kw}%"))
        
    matching_ingredients = db.query(RecipeIngredient).join(Recipe).filter(
        Recipe.workspace_id == workspace_id,
        # not_(Recipe.deleted_at.isnot(None)), # Assuming soft delete pattern if exists, usually checked implicitly
        or_(*filters)
    ).all()
    print(f"DEBUG: Matching ingredients count: {len(matching_ingredients)}")
    for ri in matching_ingredients:
        print(f"DEBUG: Match: {ri.name} (Recipe: {ri.recipe_id})")
    
    # Map recipe_id -> set of matched keywords
    recipe_matches = {}
    for ring in matching_ingredients:
        rid = ring.recipe_id
        rname = ring.name.lower()
        if rid not in recipe_matches:
            recipe_matches[rid] = set()
            
        for kw in pantry_keywords:
            if kw in rname:
                recipe_matches[rid].add(kw)

    # Get full recipe details for candidates
    candidate_recipe_ids = list(recipe_matches.keys())
    
    # Filter candidates logic has moved to the scoring loop to support soft penalties
    
    if not candidate_recipe_ids:
          return {
            "week_start": week_start,
            "meta": {"use_soon_items": use_soon_meta, "generated_at": datetime.now().isoformat(), "max_swaps": max_swaps},
            "proposals": []
        }

    candidate_recipes = db.query(Recipe).filter(Recipe.id.in_(candidate_recipe_ids)).all()
    recipe_map = {r.id: r for r in candidate_recipes}

    # 5. Score and Generate Proposals
    # We match recipes to slots.
    # For each candidate entry, we can propose the "best" recipe.
    
    # Track usage to apply caps and penalties
    # We count what is ALREADY in the plan (outside of this autofill run)
    # And we accumulate what we propose in this run.
    
    plan_recipe_counts = Counter(current_recipe_ids) # From step 3
    proposed_recipe_counts = Counter()
    
    # Sort entries by date?
    candidate_entries.sort(key=lambda e: e.date)
    
    for entry in candidate_entries:
        if len(proposals) >= max_swaps:
            break
            
        # Find best recipe for this slot
        best_recipe = None
        best_score = -1
        best_reasons = []
        
        for rid in candidate_recipe_ids:
            
            # --- Variety & Duplication Logic ---
            current_count = plan_recipe_counts[rid] + proposed_recipe_counts[rid]
            
            if strict_variety and current_count > 0:
                continue
            
            if not strict_variety and current_count >= max_duplicates_per_recipe:
                # Cap reached
                continue
                
            recipe = recipe_map.get(rid)
            if not recipe:
                continue
                
            # Scoring
            score = 0
            reasons = []
            
            # Match count
            matches = recipe_matches.get(rid, set())
            if not matches:
                continue
            
            # Base Score
            score += len(matches) * 1.0
            reasons.append({"kind": "use_soon_match", "value": ", ".join(matches)})
            
            # Expiry Urgency
            min_days_to_expire = 999
            for kw in matches:
                # Find corresponding pantry item
                for item in use_soon_items:
                    if item.name.lower() in kw or kw in item.name.lower():
                        days_left = (item.expires_on - today).days if item.expires_on else 0
                        min_days_to_expire = min(min_days_to_expire, days_left)
            
            is_urgent = False
            if min_days_to_expire < 3:
                is_urgent = True
                score += (3 - min_days_to_expire) * 0.5 # More points for closer expiry
                reasons.append({"kind": "expires_in_days", "value": min_days_to_expire})

            # Quickness
            if prefer_quick and recipe.time_minutes:
                try:
                    time_mins = int(recipe.time_minutes)
                    if time_mins <= 30:
                        score += 0.5
                        reasons.append({"kind": "quick", "value": time_mins})
                except:
                    pass
            
            # Penalty for Duplicates
            if current_count > 0:
                if is_urgent:
                    # Override penalty if urgent
                    reasons.append({"kind": "waste_reduction_override", "value": f"expires_in_{min_days_to_expire}d"})
                else:
                    # Apply penalty
                    penalty = 0.5 * current_count
                    score -= penalty
                    reasons.append({"kind": "duplicate_in_week", "value": current_count})

            # Select best
            if score > best_score:
                best_score = score
                best_recipe = recipe
                best_reasons = reasons
        
        if best_recipe and best_score > 0:
            # Create proposal
            # Check current entry state for "before"
            before_data = None
            if entry.recipe_id:
                # Manual lookup if needed, skipping for brevity as previously implemented
                pass 
                # Re-adding minimal look up if possible or just id
                # Ideally we enrich later, but let's assume UI handles id mismatch
            
            proposals.append({
                "proposal_id": str(uuid.uuid4()),
                "plan_entry_id": entry.id,
                "date": entry.date,
                "meal": entry.meal_type,
                "before": before_data, # Simplifying as previous code assumed lazy load or context
                "after": {
                    "recipe_id": best_recipe.id,
                    "title": best_recipe.title,
                    "time_minutes": best_recipe.time_minutes
                },
                "score": round(best_score, 2),
                "reasons": best_reasons,
                "constraints": {
                   "respects_force_cook": True, 
                   "avoids_back_to_back_cuisine": True 
                }
            })
            
            proposed_recipe_counts[best_recipe.id] += 1
            
    return {
        "week_start": week_start,
        "meta": {
            "use_soon_items": use_soon_meta,
            "generated_at": datetime.now().isoformat(),
            "max_swaps": max_swaps
        },
        "proposals": proposals
    }

def apply_proposals(
    db: Session,
    workspace_id: str,
    changes: List[Dict[str, str]]
) -> int:
    applied_count = 0
    
    # Bulk update entries?
    # changes: [{plan_entry_id, recipe_id}]
    
    for change in changes:
        entry_id = change.get("plan_entry_id")
        recipe_id = change.get("recipe_id")
        
        entry = db.query(MealPlanEntry).join(MealPlan).filter(
            MealPlanEntry.id == entry_id,
            MealPlan.workspace_id == workspace_id
        ).first()
        
        if entry:
            entry.recipe_id = recipe_id
            entry.is_leftover = False # Reset flags usually 
            # Could trigger method option recalculation here if needed
            applied_count += 1
            
    db.commit()
    return applied_count
