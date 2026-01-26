"""Dev-only endpoints for seeding and debugging.

Endpoints:
- POST /api/dev/seed - Create local workspace + sample recipes
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db import get_db
from ..models import Workspace, Recipe, RecipeStep, RecipeIngredient
from ..schemas import SeedResponse, WorkspaceOut
from ..ai.summary import get_client
from ..ai.utils import normalize_model_id
from ..settings import settings

router = APIRouter()


class AIPingRequest(BaseModel):
    model: Optional[str] = None

@router.post("/dev/ai/ping")
def ping_ai(body: AIPingRequest):
    """Dev-only check to see if AI model is responsive."""
    client = get_client()
    if not client:
        return {"ok": False, "error": "No API key configured"}
    
    model = normalize_model_id(body.model or settings.gemini_text_model)
    
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say 'pong' and nothing else."
        )
        return {
            "ok": True,
            "text": response.text,
            "model": model
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "model": model
        }


# Sample recipe data matching the UI prototype
SEED_RECIPES = [
    {
        "title": "Beef Casserole Leftovers",
        "cuisines": ["American", "Comfort"],
        "tags": ["leftovers", "quick"],
        "servings": 2,
        "time_minutes": 15,
        "notes": "Leftover from Sunday batch cook. Great with toast.",
        "steps": [
            {
                "step_index": 0,
                "title": "Choose reheat method",
                "bullets": [
                    "Microwave = fastest",
                    "Oven/air fryer = better texture",
                    "Add a splash of water/stock if it's dry",
                ],
                "minutes_est": 2,
            },
            {
                "step_index": 1,
                "title": "Reheat",
                "bullets": [
                    "Heat until steaming hot through the center",
                    "Stir/flip once halfway",
                    "Taste + add salt/pepper if needed",
                ],
                "minutes_est": 10,
            },
            {
                "step_index": 2,
                "title": "Plate + reset",
                "bullets": [
                    "Add something fresh (herbs, salad)",
                    "Portion remaining leftovers",
                    "Quick cleanup so tomorrow-you is happy",
                ],
                "minutes_est": 3,
            },
        ],
        "ingredients": [
            {"name": "Leftover Beef Casserole", "qty": 2, "unit": "servings", "category": "frozen"},
            {"name": "Fresh Parsley", "qty": 0.5, "unit": "bunch", "category": "produce"},
        ],
    },
    {
        "title": "Salsa Verde Enchiladas",
        "cuisines": ["Mexican"],
        "tags": ["anchor", "batch-cook"],
        "servings": 6,
        "time_minutes": 75,
        "notes": "Family favorite. Freezes great for 2-3 months.",
        "steps": [
            {
                "step_index": 0,
                "title": "Set up + prep",
                "bullets": [
                    "Pull tortillas, cheese, and sauce to the counter",
                    "Warm tortillas briefly so they don't crack",
                    "Shred chicken and taste sauce (salt/lime if needed)",
                ],
                "minutes_est": 8,
            },
            {
                "step_index": 1,
                "title": "Build the tray",
                "bullets": [
                    "Spread a thin layer of sauce in the baking dish",
                    "Fill tortillas, roll tight, and place seam-side down",
                    "Top with sauce + cheese (don't drown if sauce is thin)",
                ],
                "minutes_est": 12,
            },
            {
                "step_index": 2,
                "title": "Preheat oven + cook",
                "bullets": [
                    "Cook until cheese bubbles and edges look set",
                    "If using air fryer: work in batches or use a small pan",
                    "Rest 5 minutes before slicing",
                ],
                "minutes_est": 25,
            },
            {
                "step_index": 3,
                "title": "Serve + store",
                "bullets": [
                    "Add toppings (yogurt/sour cream, cilantro, hot sauce)",
                    "Cool leftovers before sealing",
                    "Fridge 3–4 days; freeze up to 2–3 months",
                ],
                "minutes_est": 6,
            },
        ],
        "ingredients": [
            {"name": "Chicken Breast", "qty": 1.5, "unit": "lb", "category": "protein"},
            {"name": "Salsa Verde", "qty": 1, "unit": "jar", "category": "pantry"},
            {"name": "Corn Tortillas", "qty": 12, "unit": "pcs", "category": "pantry"},
            {"name": "Monterey Jack Cheese", "qty": 8, "unit": "oz", "category": "dairy"},
            {"name": "Sour Cream", "qty": 1, "unit": "container", "category": "dairy"},
            {"name": "Cilantro", "qty": 1, "unit": "bunch", "category": "produce"},
        ],
    },
    {
        "title": "Greek Yogurt Parfait",
        "cuisines": ["Mediterranean"],
        "tags": ["breakfast", "quick", "healthy"],
        "servings": 1,
        "time_minutes": 5,
        "notes": "Use up the yogurt before it expires!",
        "steps": [
            {
                "step_index": 0,
                "title": "Layer ingredients",
                "bullets": [
                    "Start with yogurt base",
                    "Add honey drizzle",
                    "Top with granola and fresh fruit",
                ],
                "minutes_est": 3,
            },
            {
                "step_index": 1,
                "title": "Serve immediately",
                "bullets": [
                    "Eat right away for best granola crunch",
                    "Or prep in jar for grab-and-go",
                ],
                "minutes_est": 2,
            },
        ],
        "ingredients": [
            {"name": "Greek Yogurt", "qty": 1, "unit": "cup", "category": "dairy"},
            {"name": "Granola", "qty": 0.5, "unit": "cup", "category": "pantry"},
            {"name": "Berries", "qty": 0.5, "unit": "cup", "category": "produce"},
            {"name": "Honey", "qty": 1, "unit": "tbsp", "category": "pantry"},
        ],
    },
]


@router.post("/dev/seed", response_model=SeedResponse)
def seed_dev_data(db: Session = Depends(get_db)):
    """Create or update the local workspace with sample recipes.
    
    Idempotent: Running multiple times won't create duplicates.
    Returns the workspace and count of recipes created.
    """
    # Get or create local workspace
    workspace = db.query(Workspace).filter(Workspace.slug == "local").first()
    
    if not workspace:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            slug="local",
            name="Local Workspace",
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    # Count existing recipes
    existing_count = db.query(Recipe).filter(Recipe.workspace_id == workspace.id).count()
    
    created_count = 0
    for recipe_data in SEED_RECIPES:
        # Check if recipe with this title already exists
        existing = (
            db.query(Recipe)
            .filter(Recipe.workspace_id == workspace.id, Recipe.title == recipe_data["title"])
            .first()
        )
        if existing:
            continue
        
        # Create recipe
        recipe = Recipe(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            title=recipe_data["title"],
            cuisines=recipe_data.get("cuisines", []),
            tags=recipe_data.get("tags", []),
            servings=recipe_data.get("servings"),
            time_minutes=recipe_data.get("time_minutes"),
            notes=recipe_data.get("notes"),
        )
        db.add(recipe)
        
        # Create steps
        for step_data in recipe_data.get("steps", []):
            step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                step_index=step_data["step_index"],
                title=step_data["title"],
                bullets=step_data.get("bullets", []),
                minutes_est=step_data.get("minutes_est"),
            )
            db.add(step)
        
        # Create ingredients
        for ing_data in recipe_data.get("ingredients", []):
            ing = RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                name=ing_data["name"],
                qty=ing_data.get("qty"),
                unit=ing_data.get("unit"),
                category=ing_data.get("category"),
            )
            db.add(ing)

        created_count += 1
    
    db.commit()
    db.refresh(workspace)
    
    return SeedResponse(
        workspace=WorkspaceOut.model_validate(workspace),
        recipes_created=created_count,
        message=f"Created {created_count} new recipes. Total in workspace: {existing_count + created_count}",
    )
