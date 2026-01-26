"""Pydantic schemas for TasteOS API.

Request/response models for:
- Workspaces
- Recipes (with nested steps)
- Recipe images
"""

from datetime import datetime, date
from typing import Optional, Literal
from decimal import Decimal

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


# --- Recipe Ingredient ---

class RecipeIngredientOut(BaseModel):
    id: str
    name: str
    qty: Optional[float]
    unit: Optional[str]
    category: Optional[str]

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
    ingredients: list[RecipeIngredientOut] = []
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
    pantry_item_id: Optional[str] = None
    purchased_at: Optional[datetime] = None
    
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
    include_entry_ids: list[str] = []
    include_recipe_ids: list[str] = []
    ignore_leftovers: bool = False

class GrocerySkippedEntry(BaseModel):
    plan_entry_id: str
    recipe_id: str
    title: str
    reason: str
    details: Optional[dict] = None

class GroceryReducedRecipe(BaseModel):
    recipe_id: str
    title: str
    factor: float
    reason: str

class GroceryGenerationMeta(BaseModel):
    included_count: int
    skipped_count: int
    skipped_entries: list[GrocerySkippedEntry] = []
    reduced_recipes: list[GroceryReducedRecipe] = []
    carryover_items: list[dict] = [] # {name: str, reason: str, status: str}

class GroceryGenerateResponse(BaseModel):
    list: GroceryListOut
    meta: GroceryGenerationMeta

class GroceryItemUpdate(BaseModel):
    status: Optional[str] = None # need | have | purchased | optional
    qty: Optional[float] = None

# --- Cook Session ---

class TimerState(BaseModel):
    label: str
    duration_sec: int
    elapsed_sec: int = 0
    state: str = "created"
    started_at: Optional[datetime] = None
    step_index: int
    due_at: Optional[datetime] = None
    remaining_sec: Optional[int] = None
    updated_at: Optional[datetime] = None

class SessionResponse(BaseModel):
    id: str
    recipe_id: str
    status: str
    started_at: datetime
    servings_base: int
    servings_target: int
    current_step_index: int
    step_checks: dict = {}
    timers: dict[str, TimerState] = {}
    
    # Method Switching
    method_key: Optional[str] = None
    steps_override: Optional[list[dict]] = None
    method_tradeoffs: Optional[dict] = None
    method_generated_at: Optional[datetime] = None
    
    # Adjust On The Fly
    adjustments_log: list[dict] = []

    # Auto Step Detection
    auto_step_enabled: bool = False
    auto_step_mode: str = "suggest"
    auto_step_suggested_index: Optional[int] = None
    auto_step_confidence: Optional[float] = None
    auto_step_reason: Optional[str] = None

    class Config:
        from_attributes = True

class SessionPatchRequest(BaseModel):
    current_step_index: Optional[int] = Field(None, ge=0)
    step_checks_patch: Optional[dict] = None
    timers_patch: Optional[dict] = None
    timer_create: Optional[dict] = None
    timer_action: Optional[dict] = None
    servings_target: Optional[int] = Field(None, ge=1)
    
    # Auto Step Configuration
    auto_step_enabled: Optional[bool] = None
    auto_step_mode: Optional[Literal["suggest", "auto_jump"]] = None

class SessionSummaryResponse(BaseModel):
    session: dict
    highlights: list[str]
    timeline: list[dict]
    notes_suggestions: list[dict]
    stats: dict

# --- Summary Polish (v10.1) ---

class PolishedSummary(BaseModel):
    title: str
    tldr: str = Field(..., max_length=140)
    bullets: list[str]
    next_time: list[str] = Field(..., max_length=4)
    warnings: list[str] = Field(..., max_length=3)
    confidence: float
    
class SummaryPolishRequest(BaseModel):
    style: Literal["concise", "friendly", "chef"] = "concise"
    include_timeline: bool = False
    max_bullets: int = 6
    freeform_note: Optional[str] = None

class SummaryPolishResponse(BaseModel):
    polished: PolishedSummary
    raw_inputs_hash: str
    model: Optional[str]

class SessionNotesPreviewRequest(BaseModel):
    include: dict # { method: bool, servings: bool, adjustments: bool, freeform: str }
    use_ai: bool = False
    style: Literal["concise", "friendly", "chef"] = "concise"
    freeform: Optional[str] = None
    polished_data: Optional[PolishedSummary] = None

class SessionNotesPreviewResponse(BaseModel):
    proposal: dict # { recipe_patch: { notes_append: [] }, preview_markdown: str, counts: { lines: int } }

class SessionNotesApplyRequest(BaseModel):
    recipe_id: str
    notes_append: list[str]
    session_id: Optional[str] = None
    create_entry: bool = True

# --- Recipe Note Entries ---

class RecipeNoteEntryOut(BaseModel):
    id: str
    recipe_id: str
    session_id: Optional[str]
    created_at: datetime
    source: str
    title: str
    content_md: str
    tags: list[str] = []
    applied_to_recipe_notes: bool
    
    class Config:
        from_attributes = True

class RecipeNoteEntryCreate(BaseModel):
    source: str
    title: str
    content_md: str
    tags: list[str] = []
    session_id: Optional[str] = None
    apply_to_recipe_notes: bool = True

# --- Method Switcher Schemas ---

class MethodOption(BaseModel):
    key: str
    label: str
    summary: str
    warnings: list[str] = []

class MethodListResponse(BaseModel):
    methods: list[MethodOption]

class MethodPreviewRequest(BaseModel):
    method_key: str

class MethodApplyRequest(BaseModel):
    method_key: str
    steps_override: list[dict] # Should validate against RecipeStep structure ideally
    method_tradeoffs: dict

class MethodPreviewResponse(BaseModel):
    tradeoffs: dict
    steps_preview: list[dict]
    diff: Optional[dict] = None

# --- Cook Adjust Adjust-on-the-fly ---

class CookAdjustment(BaseModel):
    id: str
    step_index: int
    kind: str
    title: str
    bullets: list[str]
    warnings: list[str] = []
    confidence: float
    source: str # rules | ai | mixed

class AdjustPreviewRequest(BaseModel):
    step_index: int
    bullet_index: Optional[int] = None
    kind: str
    context: Optional[dict] = None

class AdjustPreviewResponse(BaseModel):
    adjustment: CookAdjustment
    steps_preview: list[dict]
    diff: dict

class AdjustApplyRequest(BaseModel):
    adjustment_id: str
    step_index: int
    steps_override: list[dict]
    adjustment: CookAdjustment

class AdjustUndoRequest(BaseModel):
    adjustment_id: Optional[str] = None

# --- Cook Session Events ---

class CookSessionEventOut(BaseModel):
    id: str
    session_id: str
    type: str
    meta: dict = {}
    created_at: datetime
    
    class Config:
        from_attributes = True

class StepSignal(BaseModel):
    type: str 
    step_index: Optional[int]
    meta: dict
    age_sec: int

class SessionWhyResponse(BaseModel):
    suggested_step_index: Optional[int]
    confidence: float = 0.0
    reason: Optional[str] = None
    signals: list[StepSignal] = []

# --- Insight Schemas ---

class InsightPattern(BaseModel):
    title: str
    evidence: list[str]
    confidence: float
    tags: list[str]

class InsightPlaybookItem(BaseModel):
    when: str
    do: list[str]
    avoid: list[str]

class InsightMethodTip(BaseModel):
    method: str
    tips: list[str]
    common_pitfalls: list[str]

class InsightNextFocus(BaseModel):
    goal: str
    why: str
    action: str

class InsightsResponse(BaseModel):
    headline: str
    patterns: list[InsightPattern]
    playbook: list[InsightPlaybookItem]
    method_tips: list[InsightMethodTip]
    next_focus: list[InsightNextFocus]
    model: Optional[str] = None # For debugging/transparency

class InsightsRequest(BaseModel):
    scope: Literal["workspace", "recipe"]
    recipe_id: Optional[str] = None
    window_days: int = 90
    force: bool = False
    style: Literal["coach", "concise", "chef"] = "coach"


# --- Pantry Transactions ---

class PantryTransactionOut(BaseModel):
    id: str
    pantry_item_id: str
    source: str
    ref_type: str
    ref_id: Optional[str]
    delta_qty: Optional[Decimal]
    unit: Optional[str]
    note: Optional[str]
    created_at: datetime
    undone_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Leftovers ---

class LeftoverBase(BaseModel):
    name: str
    expires_on: Optional[date] = None
    servings_left: Optional[Decimal] = None
    notes: Optional[str] = None

class LeftoverCreate(LeftoverBase):
    plan_entry_id: Optional[str] = None
    recipe_id: Optional[str] = None

class LeftoverUpdate(BaseModel):
    name: Optional[str] = None
    expires_on: Optional[date] = None
    servings_left: Optional[Decimal] = None
    notes: Optional[str] = None
    consumed_at: Optional[datetime] = None

class LeftoverOut(LeftoverBase):
    id: str
    workspace_id: str
    plan_entry_id: Optional[str]
    recipe_id: Optional[str]
    pantry_item_id: Optional[str]
    created_at: datetime
    consumed_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Pantry Decrement ---

class PantryDecrementItem(BaseModel):
    ingredient_name: str
    pantry_item_id: Optional[str]
    pantry_item_name: Optional[str]
    qty_needed: float
    qty_available: Optional[float]
    unit: Optional[str]
    match_confidence: float # 1.0 = exact, 0.0 = none

class PantryDecrementPreviewResponse(BaseModel):
    items: list[PantryDecrementItem]

class PantryDecrementApplyRequest(BaseModel):
    force: bool = False
    items: Optional[list[PantryDecrementItem]] = None # If provided, use these override values
