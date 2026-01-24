"""Pydantic schemas for TasteOS API.

Request/response models for:
- Workspaces
- Recipes (with nested steps)
- Recipe images
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Workspace ---

class WorkspaceOut(BaseModel):
    id: str
    slug: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Recipe Step ---

class RecipeStepCreate(BaseModel):
    step_index: int = Field(..., ge=0)
    title: str = Field(..., min_length=1, max_length=200)
    bullets: Optional[list[str]] = None
    minutes_est: Optional[int] = Field(None, ge=0)


class RecipeStepOut(BaseModel):
    id: str
    step_index: int
    title: str
    bullets: Optional[list[str]]
    minutes_est: Optional[int]

    class Config:
        from_attributes = True


# --- Recipe Image ---

class RecipeImageOut(BaseModel):
    id: str
    status: str  # pending | ready | failed
    provider: Optional[str]
    model: Optional[str]
    prompt: Optional[str]
    storage_key: Optional[str]
    width: Optional[int]
    height: Optional[int]
    public_url: Optional[str] = None  # Constructed from storage_key
    created_at: datetime

    class Config:
        from_attributes = True


# --- Recipe ---

class RecipeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    cuisines: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    servings: Optional[int] = Field(None, ge=1)
    time_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    steps: Optional[list[RecipeStepCreate]] = None


class RecipePatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    cuisines: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    servings: Optional[int] = Field(None, ge=1)
    time_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    steps: Optional[list[RecipeStepCreate]] = None  # Replaces all steps if provided


class RecipeOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    cuisines: Optional[list[str]]
    tags: Optional[list[str]]
    servings: Optional[int]
    time_minutes: Optional[int]
    notes: Optional[str]
    steps: list[RecipeStepOut] = []
    images: list[RecipeImageOut] = []
    primary_image_url: Optional[str] = None  # Convenience field
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeListOut(BaseModel):
    """Lighter recipe model for list views (no steps)."""
    id: str
    workspace_id: str
    title: str
    cuisines: Optional[list[str]]
    tags: Optional[list[str]]
    servings: Optional[int]
    time_minutes: Optional[int]
    primary_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Dev Seed ---

class SeedResponse(BaseModel):
    workspace: WorkspaceOut
    recipes_created: int
    message: str


# --- Image Generation ---

class ImageGenerateResponse(BaseModel):
    image_id: str
    status: str  # pending | ready | failed
    message: str


class ImageStatusResponse(BaseModel):
    image_id: Optional[str]
    status: str  # pending | ready | failed | none
    public_url: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    prompt: Optional[str]

# --- Pantry ---

from datetime import date

class PantryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    qty: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    expires_on: Optional[date] = None
    source: str = "manual"
    notes: Optional[str] = None

class PantryItemCreate(PantryItemBase):
    pass

class PantryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    qty: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    expires_on: Optional[date] = None
    source: Optional[str] = None
    notes: Optional[str] = None

class PantryItemOut(PantryItemBase):
    id: str
    workspace_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Grocery ---

class GroceryListItemOut(BaseModel):
    id: str
    name: str
    qty: Optional[float]
    unit: Optional[str]
    category: Optional[str]
    status: str
    reason: Optional[str]
    
    class Config:
        from_attributes = True

class GroceryListOut(BaseModel):
    id: str
    source: Optional[str]
    created_at: datetime
    items: list[GroceryListItemOut] = []
    
    class Config:
        from_attributes = True

class GenerateGroceryRequest(BaseModel):
    recipe_ids: list[str] = []
    plan_id: Optional[str] = None

class GroceryItemUpdate(BaseModel):
    status: Optional[str] = None # need | have | purchased | optional
    qty: Optional[float] = None
