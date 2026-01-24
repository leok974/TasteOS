from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# --- Portable Sub-Models ---

class PortableIngredient(BaseModel):
    name: str
    qty: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None

class PortableStep(BaseModel):
    step_index: int
    title: str
    bullets: List[str] = []
    minutes_est: Optional[int] = None

class PortableImageMeta(BaseModel):
    source: Optional[str] = None
    prompt: Optional[str] = None
    # We explicitly do NOT include storage_key or public_url 

class PortableRecipeDetail(BaseModel):
    title: str
    cuisines: List[str] = []
    tags: List[str] = []
    servings: Optional[int] = None
    time_minutes: Optional[int] = None
    notes: Optional[str] = None
    
    ingredients: List[PortableIngredient] = []
    steps: List[PortableStep] = []
    image_meta: Optional[PortableImageMeta] = None

# --- Main Portable Payload ---

class PortableRecipe(BaseModel):
    schema_version: str = "tasteos.recipe.v1"
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    recipe: PortableRecipeDetail
