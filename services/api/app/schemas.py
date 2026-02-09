"""Pydantic schemas for TasteOS API.

Request/response models for:
- Workspaces
- Recipes (with nested steps)
- Recipe images
"""

from datetime import datetime, date
from typing import Optional, Literal, List, Union
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




# --- Recipe Variant ---

class RecipeVariantOut(BaseModel):
    id: str
    recipe_id: str
    label: str
    content_json: dict
    created_at: datetime
    created_by: str
    model_id: Optional[str] = None
    prompt_version: Optional[str] = None

    class Config:
        from_attributes = True

class RecipeVariantCreate(BaseModel):
    label: str
    content_json: dict

class RecipeVariantListOut(BaseModel):
    id: str
    label: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Draft / Chat Integration ---

class DraftStepIn(BaseModel):
    title: str
    bullets: List[str]
    minutes: int = 0

class RecipeDraftIn(BaseModel):
    title: str
    yield_data: Optional[dict] = Field(None, alias="yield")
    tags: Optional[list[str]] = None
    equipment: Optional[list[str]] = None
    ingredients: list[dict]
    steps: List[Union[DraftStepIn, str]]
    storage: Optional[list[dict]] = None
    reheat: Optional[list[dict]] = None
    nutrition_estimate: Optional[dict] = None

class RecipeFromDraftCreate(BaseModel):
    workspace_id: str
    draft: RecipeDraftIn
    label: str = "Original"
    source: str = "ai"
    model_id: Optional[str] = None
    prompt_version: Optional[str] = None

class RecipeVariantFromDraftCreate(BaseModel):
    workspace_id: str
    draft: RecipeDraftIn
    label: str
    base_variant_id: Optional[str] = None
    source: str = "ai"
    model_id: Optional[str] = None
    prompt_version: Optional[str] = None

class SetActiveVariantRequest(BaseModel):
    workspace_id: str
    variant_id: str



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
    
    # Versioning
    active_variant_id: Optional[str] = None
    active_variant: Optional[RecipeVariantOut] = None
    variants: list[RecipeVariantOut] = []
    
    # Cook Time Badge
    total_minutes: Optional[int] = None
    total_minutes_source: Optional[str] = None
    
    primary_image_url: Optional[str] = None  # Convenience field
    created_at: datetime

    class Config:
        from_attributes = True


# --- Recipe Chat / Assist ---

class RecipeAssistMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    
class RecipeAssistRequest(BaseModel):
    messages: list[RecipeAssistMessage]
    mode: str = "recipe"

class RecipeAssistResponse(BaseModel):
    reply: str
    used_ai: bool
    reason: Optional[str]
    suggested: list[str]


class RecipeListOut(BaseModel):
    """Lighter recipe model for list views (no steps)."""
    id: str
    workspace_id: str
    title: str
    cuisines: Optional[list[str]]
    tags: Optional[list[str]]
    servings: Optional[int]
    
    # We want total_minutes here for the list view badge
    total_minutes: Optional[int] = None
    total_minutes_source: Optional[str] = None
    time_minutes: Optional[int] # Keep legacy
    
    primary_image_url: Optional[str] = None
    created_at: datetime
    
    active_variant_id: Optional[str] = None
    variants: list[RecipeVariantListOut] = []

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
    opened_on: Optional[date] = None
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
    opened_on: Optional[date] = None
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
    
    # Transient fields (calculated at runtime)
    expiry_days: Optional[int] = None

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
    paused_at: Optional[datetime] = None
    done_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
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
    state_version: int = 1
    step_checks: dict = {}
    timers: dict[str, TimerState] = {}
    hands_free: Optional[dict] = None
    
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
    mark_step_complete: Optional[int] = None # v13.3: Atomic step completion
    timers_patch: Optional[dict] = None
    timer_create: Optional[dict] = None
    timer_action: Optional[dict] = None
    servings_target: Optional[int] = Field(None, ge=1)
    
    # Auto Step Configuration
    auto_step_enabled: Optional[bool] = None
    auto_step_mode: Optional[Literal["suggest", "auto_jump"]] = None

# --- V13 Timers ---

class TimerResponse(BaseModel):
    id: str
    client_id: Optional[str] = None
    label: str
    step_index: int
    duration_sec: int
    state: str  # created, running, paused, done
    created_at: str
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    done_at: Optional[str] = None
    deleted_at: Optional[str] = None
    remaining_sec: Optional[int] = None # For legacy compat or snapshot
    
    class Config:
        from_attributes = True

class TimerCreateRequest(BaseModel):
    client_id: str
    label: str
    step_index: int
    duration_s: int

class TimerActionRequest(BaseModel):
    action: Literal["start", "pause", "resume", "done", "delete"]

class TimerPatchRequest(BaseModel):
    label: Optional[str] = None
    duration_s: Optional[int] = None
    step_index: Optional[int] = None

class CookNextAction(BaseModel):
    type: str # go_to_step, start_timer, create_timer, mark_step_done
    label: str
    step_idx: Optional[int] = None
    timer_id: Optional[str] = None
    duration_s: Optional[int] = None

class CookNextResponse(BaseModel):
    suggested_step_idx: int
    actions: list[CookNextAction]
    reason: str

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


# --- Recipe Macro Entries ---

class RecipeMacroEntryOut(BaseModel):
    id: str
    recipe_id: str
    created_at: datetime
    
    # Macros
    calories_min: Optional[int] = None
    calories_max: Optional[int] = None
    protein_min: Optional[int] = None
    protein_max: Optional[int] = None
    carbs_min: Optional[int] = None
    carbs_max: Optional[int] = None
    fat_min: Optional[int] = None
    fat_max: Optional[int] = None

    source: str
    confidence: Optional[float] = None
    model: Optional[str] = None
    
    class Config:
        from_attributes = True

class RecipeMacroEntryCreate(BaseModel):
    # Macros
    calories_min: Optional[int] = None
    calories_max: Optional[int] = None
    protein_min: Optional[int] = None
    protein_max: Optional[int] = None
    carbs_min: Optional[int] = None
    carbs_max: Optional[int] = None
    fat_min: Optional[int] = None
    fat_max: Optional[int] = None

    source: str = "user"


class EstimateMacrosRequest(BaseModel):
    persist: bool = False


# --- Recipe Tip Entries ---

class RecipeTipEntryOut(BaseModel):
    id: str
    recipe_id: str
    created_at: datetime
    scope: str
    tips_json: list[str]
    food_safety_json: list[str]
    source: str
    confidence: Optional[float] = None
    model: Optional[str] = None
    
    class Config:
        from_attributes = True

class RecipeTipEntryCreate(BaseModel):
    tips_json: list[str] = []
    food_safety_json: list[str] = []
    source: str = "user"


class EstimateTipsRequest(BaseModel):
    scope: str  # storage | reheat
    persist: bool = False


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

class TimerSuggestion(BaseModel):
    client_id: str
    label: str
    step_index: int
    duration_s: int
    reason: str

class TimerSuggestionResponse(BaseModel):
    suggested: List[TimerSuggestion]

class TimerFromSuggestedRequest(BaseModel):
    client_ids: List[str]
    autostart: bool = False

# --- Cook Completion & Learnings ---

class CookCompleteRequest(BaseModel):
    servings_made: Optional[float] = None
    leftover_servings: Optional[float] = None
    create_leftover: bool = False
    final_notes: Optional[str] = None

class CookRecap(BaseModel):
    final_step_index: int
    completion_rate: float
    timers_used: List[dict]
    adjustments: List[dict]
    servings_made: Optional[float]
    leftovers_created: bool

class CookCompleteResponse(BaseModel):
    session_id: str
    completed_at: datetime
    recap: CookRecap
    note_entry_id: Optional[str]
    leftover_id: Optional[str]

class RecipeLearningsResponse(BaseModel):
    highlights: List[str]
    common_tags: List[str]
    recent_recaps: List[dict]


# --- Unit Conversion ---

class UnitConvertRequest(BaseModel):
    qty: float
    from_unit: str
    to_unit: Optional[str] = None # If None, auto-select based on prefs
    target_system: Optional[Literal["metric", "us_customary", "imperial"]] = None # Override prefs
    ingredient_name: Optional[str] = None
    force_cross_type: Optional[bool] = None # Overrides prefs if set

class UnitConvertResponse(BaseModel):
    qty: float
    unit: str
    confidence: Literal["high", "medium", "low", "none"]
    note: Optional[str] = None
    is_approx: bool = False


    density_used_g_per_ml: Optional[float] = None
    density_source: Optional[Literal["override", "common", "none"]] = None
    
# --- Preferences ---

class UnitPrefs(BaseModel):
    system: Literal["us", "metric"] = "us"
    rounding: Literal["cook", "decimal"] = "cook"
    decimal_places: int = 2
    prefer_mass: List[str] = ["oz", "lb", "g", "kg"]
    prefer_volume: List[str] = ["tsp", "tbsp", "cup", "ml", "l"]
    prefer_temp: Literal["F", "C"] = "F"
    allow_cross_type: bool = True
    density_policy: Literal["known_only", "common_only"] = "common_only"
    
class UnitDensityInput(BaseModel):
    mass_value: float
    mass_unit: str
    vol_value: float = 1.0
    vol_unit: str = "cup"

class IngredientDensityUpsert(BaseModel):
    ingredient_name: str
    density: UnitDensityInput

class IngredientDensityOut(BaseModel):
    id: str
    ingredient_key: str
    display_name: str
    density_g_per_ml: float
    source: str
    updated_at: datetime
    
    class Config:
        from_attributes = True

class IngredientDensityListResponse(BaseModel):
    items: List[IngredientDensityOut]

class UnitPrefsUpdate(BaseModel):
    # Partial update, so all optional
    system: Optional[Literal["us", "metric"]] = None
    rounding: Optional[Literal["cook", "decimal"]] = None
    decimal_places: Optional[int] = None
    prefer_mass: Optional[List[str]] = None
    prefer_volume: Optional[List[str]] = None
    prefer_temp: Optional[Literal["F", "C"]] = None
    allow_cross_type: Optional[bool] = None
    density_policy: Optional[Literal["known_only", "common_only"]] = None

class UserPrefsResponse(BaseModel):
    unit_prefs: UnitPrefs


# --- Autoflow (v15.2.2) ---

class AutoflowClientState(BaseModel):
    checked_keys: list[str] = []
    active_timer_ids: list[str] = []

class AutoflowRequest(BaseModel):
    step_index: int
    mode: str = "quick"
    client_state: AutoflowClientState = Field(default_factory=AutoflowClientState)


# --- Chef Chat (Craft Recipes) ---

class ChefChatRequest(BaseModel):
    message: str
    mode: Literal["create", "refine"] = "create"
    thread_id: Optional[str] = None
    
    # For Refine mode
    recipe_id: Optional[str] = None
    base_variant_id: Optional[str] = None
    
    # Optional constraints
    context_recipe_ids: Optional[list[str]] = None

class ChefChatResponse(BaseModel):
    assistant_message: str
    recipe_draft: dict  # The structured recipe JSON
    suggested_label: Optional[str] = None
    
    # Metadata
    source: str = "ai"
    model_id: Optional[str] = None
    prompt_version: Optional[str] = None
    thread_id: Optional[str] = None

    mode: str = "quick"  # quick | deep
    client_state: AutoflowClientState = Field(default_factory=AutoflowClientState)

class AutoflowActionPayload(BaseModel):
    # Flexible payload for different action types
    minutes: Optional[int] = None
    label: Optional[str] = None
    step_index: Optional[int] = None
    key: Optional[str] = None # For checks
    value: Optional[bool] = None

class AutoflowAction(BaseModel):
    op: Literal["create_timer", "patch_session", "navigate_step", "open_help", "none"]
    payload: dict = {}

class AutoflowSuggestion(BaseModel):
    type: str # start_timer | check_item | next_step | open_help | prep_next | safety | complete_step
    label: str
    action: AutoflowAction
    confidence: Literal["high", "medium", "low"]
    why: Optional[str] = None

class AutoflowResponse(BaseModel):
    suggestions: list[AutoflowSuggestion]
    source: str # ai | heuristic
    autoflow_id: str

# --- Grocery V2 ---

class GroveryV2Scope(BaseModel):
    start: date
    days: Optional[List[date]] = None
    meals: Optional[List[str]] = None

class GroceryGenerateV2Request(BaseModel):
    start: date
    days: Optional[List[date]] = None
    meals: Optional[List[str]] = None

class GrocerySource(BaseModel):
    recipe_id: str
    recipe_title: str
    line: Optional[str] = None

class GroceryItemV2(BaseModel):
    key: str
    display: str
    quantity: Optional[float]
    unit: Optional[str]
    raw: List[str]
    sources: List[GrocerySource]

class GroceryUnparsedV2(BaseModel):
    raw: str
    sources: List[GrocerySource]

class GroceryV2Response(BaseModel):
    scope: GroveryV2Scope
    items: List[GroceryItemV2]
    unparsed: List[GroceryUnparsedV2]
