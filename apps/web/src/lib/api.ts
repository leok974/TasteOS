/**
 * TasteOS API Client
 * 
 * Fetches from the FastAPI backend at /api/*
 */

// Defaults to same-origin /api proxy to avoid CORS/mixed-content
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

function join(base: string, path: string) {
    const b = base.endsWith("/") ? base.slice(0, -1) : base;
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${b}${p}`;
}

// --- Types ---

let currentWorkspaceId: string | null = null;
export function newIdemKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older environments or non-secure contexts
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export function setApiWorkspaceId(id: string | null) {
  currentWorkspaceId = id;
}

function getHeaders(init?: RequestInit) {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (currentWorkspaceId) {
    headers.set("X-Workspace-Id", currentWorkspaceId);
  }
  return headers;
}

export interface RecipeStep {
  id: string;
  step_index: number;
  title: string;
  bullets: string[] | null;
  minutes_est: number | null;
}

export interface RecipeImage {
  id: string;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  provider: string | null;
  model: string | null;
  prompt: string | null;
  storage_key: string | null;
  public_url: string | null;
  created_at: string;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface RecipeNoteEntry {
  id: string;
  recipe_id: string;
  session_id: string | null;
  source: string;
  title: string;
  content_md: string;
  created_at: string;
  tags?: string[];
}

export interface Recipe {
  id: string;
  workspace_id: string;
  title: string;
  cuisines: string[] | null;
  tags: string[] | null;
  servings: number | null;
  time_minutes: number | null;
  notes: string | null;
  ingredients: { name: string; qty: number | null; unit: string | null; category: string | null }[];
  steps: RecipeStep[];
  images: RecipeImage[];
  primary_image_url: string | null;
  created_at: string;
}

export interface RecipeListItem {
  id: string;
  workspace_id: string;
  title: string;
  cuisines: string[] | null;
  tags: string[] | null;
  servings: number | null;
  time_minutes: number | null;
  primary_image_url: string | null;
  created_at: string;
}

export interface RecipeCreateInput {
  title: string;
  cuisines?: string[];
  tags?: string[];
  servings?: number;
  time_minutes?: number;
  notes?: string;
  steps?: {
    step_index: number;
    title: string;
    bullets?: string[];
    minutes_est?: number;
  }[];
}

export interface SeedResponse {
  workspace: {
    id: string;
    slug: string;
    name: string;
    created_at: string;
  };
  recipes_created: number;
  message: string;
}

// --- API Functions ---

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: getHeaders()
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(errorData.detail || `GET ${path} failed: ${res.status}`);
    (error as any).status = res.status;
    throw error;
  }
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown, options: { idempotent?: boolean } = {}): Promise<T> {
  const headers = getHeaders();
  if (options.idempotent) {
    headers.set("Idempotency-Key", newIdemKey());
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(errorData.detail || `POST ${path} failed: ${res.status}`);
    (error as any).status = res.status;
    throw error;
  }
  return res.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(errorData.detail || `PATCH ${path} failed: ${res.status}`);
    (error as any).status = res.status;
    throw error;
  }
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(errorData.detail || `DELETE ${path} failed: ${res.status}`);
    (error as any).status = res.status;
    throw error;
  }
  // Some DELETE endpoints return empty body
  if (res.status === 204) return {} as T;
  return res.json().catch(() => ({} as T));
}

// --- Recipe API ---

export async function fetchRecipes(params?: { search?: string; limit?: number }): Promise<RecipeListItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set('search', params.search);
  if (params?.limit) searchParams.set('limit', String(params.limit));

  const query = searchParams.toString();
  return apiGet<RecipeListItem[]>(`/recipes${query ? `?${query}` : ''}`);
}

export async function fetchRecipe(id: string): Promise<Recipe> {
  return apiGet<Recipe>(`/recipes/${id}`);
}

export async function createRecipe(data: RecipeCreateInput): Promise<Recipe> {
  return apiPost<Recipe>('/recipes', data, { idempotent: true });
}

export async function updateRecipe(id: string, data: Partial<RecipeCreateInput>): Promise<Recipe> {
  return apiPatch<Recipe>(`/recipes/${id}`, data);
}

export async function seedDevData(): Promise<SeedResponse> {
  return apiPost<SeedResponse>('/dev/seed', undefined, { idempotent: true });
}

// --- Image Generation ---

export interface ImageStatus {
  image_id: string | null;
  status: 'none' | 'pending' | 'processing' | 'ready' | 'failed';
  public_url: string | null;
  provider: string | null;
  model: string | null;
  prompt: string | null;
}

export interface ImageGenerateResponse {
  image_id: string;
  status: string;
  message: string;
}

export async function fetchImageStatus(recipeId: string): Promise<ImageStatus> {
  return apiGet<ImageStatus>(`/recipes/${recipeId}/image`);
}

export async function generateImage(recipeId: string): Promise<ImageGenerateResponse> {
  return apiPost<ImageGenerateResponse>(`/recipes/${recipeId}/image/generate`, undefined, { idempotent: true });
}

export async function regenerateImage(recipeId: string): Promise<ImageGenerateResponse> {
  return apiPost<ImageGenerateResponse>(`/recipes/${recipeId}/image/regenerate`, undefined, { idempotent: true });
}


// --- Share / Import / Export ---

export interface PortableRecipe {
  schema_version: string;
  recipe: {
    title: string;
    ingredients: { name: string; qty?: number; unit?: string; category?: string }[];
    steps: { step_index: number; title: string; bullets?: string[]; minutes_est?: number }[];
    // ... we can add more fields if needed for UI, but backend validates it.
    [key: string]: any;
  }
}

export interface ImportResult {
  recipe_id: string;
  created: boolean;
  deduped: boolean;
  message: string;
}

export async function exportRecipe(id: string, download = false): Promise<PortableRecipe> {
  const query = download ? "?download=1" : "";
  // If download is true, the browser handles the file download via direct navigation or blob.
  // apiGet returns JSON. If download=1, we might get a Blob (handled differently?)
  // Actually, for download=1 it sets Content-Disposition attachment. fetch can still read it.
  return apiGet<PortableRecipe>(`/recipes/${id}/export${query}`);
}

export async function importRecipe(payload: PortableRecipe, mode: 'dedupe' | 'copy' = 'dedupe', regenImage = false): Promise<ImportResult> {
  const query = new URLSearchParams({ mode, regen_image: regenImage ? '1' : '0' });
  return apiPost<ImportResult>(`/recipes/import?${query.toString()}`, payload, { idempotent: true });
}

// --- Pantry API ---

export interface PantryItem {
  id: string;
  workspace_id: string;
  name: string;
  qty?: number;
  unit?: string;
  category?: string;
  expires_on?: string; // YYYY-MM-DD
  opened_on?: string; // YYYY-MM-DD
  source: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// --- Autofill API ---

export interface AutofillProposal {
  proposal_id: string;
  plan_entry_id: string;
  date: string;
  meal: string;
  before?: {
    recipe_id: string;
    title: string;
    time_minutes?: number;
  };
  after: {
    recipe_id: string;
    title: string;
    time_minutes?: number;
  };
  score: number;
  reasons: Array<{ kind: string; value: string | number }>;
}

export interface AutofillResponse {
  week_start: string;
  meta: {
    use_soon_items: Array<{ name: string; expires_in_days: number }>;
  };
  proposals: AutofillProposal[];
}

export async function generateAutofillProposals(weekStart: string, options?: { strictVariety?: boolean }): Promise<AutofillResponse> {
  return apiPost<AutofillResponse>(`/autofill/use-soon?week_start=${weekStart}`, {
    days: 5,
    max_swaps: 4,
    slots: ["dinner"],
    prefer_quick: true,
    strict_variety: options?.strictVariety ?? false
  });
}

export async function applyAutofillProposals(weekStart: string, changes: Array<{ plan_entry_id: string; recipe_id: string }>): Promise<{ applied: number }> {
  return apiPost<{ applied: number }>("/autofill/use-soon/apply", {
    week_start: weekStart,
    changes
  }, { idempotent: true });
}

// --- Pantry API ---

export type CreatePantryItem = Omit<PantryItem, "id" | "workspace_id" | "created_at" | "updated_at">;
export type UpdatePantryItem = Partial<CreatePantryItem>;

export async function fetchPantryItems(params?: { search?: string; useSoon?: boolean }): Promise<PantryItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("q", params.search);

  if (params?.useSoon) {
    // Use the specific endpoint for sorted results
    return apiGet<PantryItem[]>("/pantry/use-soon?days=5");
  }

  return apiGet<PantryItem[]>(`/pantry/?${searchParams.toString()}`);
}

export async function createPantryItem(item: CreatePantryItem): Promise<PantryItem> {
  return apiPost<PantryItem>("/pantry/", item, { idempotent: true });
}

export async function updatePantryItem(id: string, item: UpdatePantryItem): Promise<PantryItem> {
  return apiPatch<PantryItem>(`/pantry/${id}`, item);
}

export async function deletePantryItem(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/pantry/${id}`, {
    method: "DELETE",
    headers: getHeaders()
  });
  if (!res.ok) throw new Error(`DELETE /pantry/${id} failed`);
}

// --- Grocery API ---

export interface GroceryListItem {
  id: string;
  name: string;
  qty?: number;
  unit?: string;
  category?: string;
  status: 'need' | 'have' | 'optional' | 'purchased';
  reason?: string;
  pantry_item_id?: string;
  expiry_days?: number; // Runtime calculated
}

export interface GrocerySkippedEntry {
  plan_entry_id: string;
  recipe_id: string;
  title: string;
  reason: string;
}

export interface GroceryReducedRecipe {
  recipe_id: string;
  title: string;
  factor: number;
  reason: string;
}

export interface GroceryGenerationMeta {
  included_count: number;
  skipped_count: number;
  skipped_entries: GrocerySkippedEntry[];
  reduced_recipes: GroceryReducedRecipe[];
}

export interface GroceryGenerateResponse {
  list: GroceryList;
  meta: GroceryGenerationMeta;
}

export interface GroceryList {
  id: string;
  source?: string;
  created_at: string;
  items: GroceryListItem[];
  meta?: GroceryGenerationMeta;
}

export async function generateGroceryList(params: { recipeIds?: string[]; planId?: string; includeEntryIds?: string[] }): Promise<GroceryList> {
  // Response is { list: ..., meta: ... }
  const res = await apiPost<GroceryGenerateResponse>("/grocery/generate", {
    recipe_ids: params.recipeIds || [],
    plan_id: params.planId,
    include_entry_ids: params.includeEntryIds || []
  }, { idempotent: true });

  // Attach meta to list for uniform handling
  return {
    ...res.list,
    meta: res.meta
  };
}

export async function fetchCurrentGroceryList(recompute: boolean = false): Promise<GroceryList> {
  const query = recompute ? "?recompute=true" : "";
  return apiGet<GroceryList>(`/grocery/current${query}`);
}

export async function clearGroceryList(): Promise<void> {
  return apiDelete<void>(`/grocery/current`);
}

export async function updateGroceryItem(id: string, data: { status?: string; qty?: number }): Promise<GroceryListItem> {
  return apiPatch<GroceryListItem>(`/grocery/items/${id}`, data);
}

// --- Cook Session & Method Switching ---

export interface CookTimer {
  label: string;
  duration_sec: number;
  elapsed_sec: number;
  state: 'created' | 'running' | 'paused' | 'done';
  started_at: string | null;
  paused_at?: string | null;
  step_index: number;
  deleted_at?: string | null;
}

export interface TimerSuggestion {
  client_id: string;
  label: string;
  step_index: number;
  duration_s: number;
  reason: string;
}

export interface CookSession {
  id: string;
  recipe_id: string;
  status: 'active' | 'completed' | 'abandoned';
  started_at: string;
  servings_base: number;
  servings_target: number;
  current_step_index: number;
  step_checks: Record<string, boolean>;
  timers: Record<string, CookTimer>;

  // Method Switching
  method_key?: string | null;
  steps_override?: RecipeStep[] | null;
  method_tradeoffs?: Record<string, any> | null;
  method_generated_at?: string | null;

  // AdjustOnTheFly
  adjustments_log?: any[];

  // Auto Step Detection
  auto_step_enabled: boolean;
  auto_step_mode?: 'suggest' | 'auto_jump';
  auto_step_suggested_index?: number | null;
  auto_step_confidence?: number | null;
  auto_step_reason?: string | null;
}

export interface MethodOption {
  key: string;
  label: string;
  summary: string;
  warnings: string[];
}

export interface MethodListResponse {
  methods: MethodOption[];
}

export interface MethodPreviewResponse {
  tradeoffs: {
    time_delta_min: number;
    effort: string;
    cleanup: string;
    texture_notes: string[];
    risks: string[];
  };
  steps_preview: RecipeStep[];
  diff?: any; // MVP: generic obj
}

export async function fetchCookMethods(): Promise<MethodListResponse> {
  return apiGet<MethodListResponse>(`/cook/methods`);
}

export async function previewCookMethod(sessionId: string, methodKey: string): Promise<MethodPreviewResponse> {
  return apiPost<MethodPreviewResponse>(`/cook/session/${sessionId}/method/preview`, { method_key: methodKey }, { idempotent: true });
}

export async function applyCookMethod(sessionId: string, methodKey: string, steps: RecipeStep[], tradeoffs: any): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/method/apply`, {
    method_key: methodKey,
    steps_override: steps,
    method_tradeoffs: tradeoffs
  }, { idempotent: true });
}

export async function resetCookMethod(sessionId: string): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/method/reset`, undefined, { idempotent: true });
}

export async function apiPatchSession(sessionId: string, patch: any): Promise<CookSession> {
  return apiPatch<CookSession>(`/cook/session/${sessionId}`, patch);
}

// --- Cook Assist: Smart Timers ---

export async function getTimerSuggestions(sessionId: string): Promise<{ suggested: TimerSuggestion[] }> {
  return apiGet<{ suggested: TimerSuggestion[] }>(`/cook/session/${sessionId}/timers/suggested`);
}

export async function createTimersFromSuggestions(
  sessionId: string, 
  clientIds: string[], 
  autostart: boolean = true
): Promise<{ created: number; timers: Record<string, CookTimer> }> {
  return apiPost<{ created: number; timers: Record<string, CookTimer> }>(
    `/cook/session/${sessionId}/timers/from-suggested`,
    { client_ids: clientIds, autostart },
    { idempotent: true }
  );
}

// --- Cook Adjust Types ---

export type AdjustmentKind =
  | 'too_salty'
  | 'too_spicy'
  | 'too_thick'
  | 'too_thin'
  | 'burning'
  | 'no_browning'
  | 'undercooked';

export interface CookAdjustment {
  id: string;
  step_index: number;
  kind: AdjustmentKind;
  title: string;
  bullets: string[];
  warnings: string[];
  confidence: number;
  source: string;
}

export interface AdjustPreviewRequest {
  step_index: number;
  bullet_index?: number;
  kind: AdjustmentKind;
  context?: Record<string, any>;
}

export interface AdjustPreviewResponse {
  adjustment: CookAdjustment;
  steps_preview: any[]; // Full steps structure
  diff: {
    step_index: number;
    changed_fields: string[];
    before: { title: string; bullets: string[] };
    after: { title: string; bullets: string[] };
  };
}

export interface AdjustApplyRequest {
  adjustment_id: string;
  step_index: number;
  steps_override: any[];
  adjustment: CookAdjustment;
}

// --- Endpoints ---

export async function previewAdjustment(
  sessionId: string,
  req: AdjustPreviewRequest
): Promise<AdjustPreviewResponse> {
  return apiPost<AdjustPreviewResponse>(`/cook/session/${sessionId}/adjust/preview`, req, { idempotent: true });
}

export async function applyAdjustment(
  sessionId: string,
  req: AdjustApplyRequest
): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/adjust/apply`, req, { idempotent: true });
}


// --- Insights ---

export interface InsightPattern {
  title: string;
  evidence: string[];
  confidence: number;
  tags: string[];
}

export interface InsightPlaybookItem {
  when: string;
  do: string[];
  avoid: string[];
}

export interface InsightMethodTip {
  method: string;
  tips: string[];
  common_pitfalls: string[];
}

export interface InsightNextFocus {
  goal: string;
  why: string;
  action: string;
}

export interface InsightsResponse {
  headline: string;
  patterns: InsightPattern[];
  playbook: InsightPlaybookItem[];
  method_tips: InsightMethodTip[];
  next_focus: InsightNextFocus[];
  model?: string;
}

export interface InsightsRequest {
  scope: "workspace" | "recipe";
  recipe_id?: string | null;
  window_days?: number;
  force?: boolean;
  style?: "coach" | "concise" | "chef";
}

export async function fetchInsights(params: InsightsRequest): Promise<InsightsResponse> {
  return apiPost<InsightsResponse>("/insights/notes", params, { idempotent: true });
}

// --- V13 Timers ---

export interface TimerResponse {
  id: string;
  client_id?: string;
  label: string;
  step_index: number;
  duration_sec: number;
  state: 'created' | 'running' | 'paused' | 'done';
  created_at: string;
  started_at?: string | null;
  paused_at?: string | null;
  done_at?: string | null;
  deleted_at?: string | null;
}

export interface TimerCreateRequest {
  client_id: string;
  label: string;
  step_index: number;
  duration_s: number;
}

export interface TimerActionRequest {
  action: 'start' | 'pause' | 'resume' | 'done' | 'delete';
}

export interface TimerPatchRequest {
  label?: string;
  duration_s?: number;
  step_index?: number;
}

export async function cookTimerCreate(sessionId: string, payload: TimerCreateRequest): Promise<TimerResponse> {
  return apiPost<TimerResponse>(`/cook/session/${sessionId}/timers`, payload, { idempotent: true });
}

export async function cookTimerAction(sessionId: string, timerId: string, payload: TimerActionRequest): Promise<TimerResponse> {
  return await apiPost<TimerResponse>(`/cook/session/${sessionId}/timers/${timerId}/action`, payload, { idempotent: true });
}

export async function cookTimerPatch(sessionId: string, timerId: string, payload: TimerPatchRequest): Promise<TimerResponse> {
  return apiPatch<TimerResponse>(`/cook/session/${sessionId}/timers/${timerId}`, payload);
}

// --- Cook Assist v13.1 ---

export interface CookNextAction {
  type: string; // go_to_step, start_timer, create_timer, mark_step_done, complete_session
  label: string;
  step_idx?: number;
  timer_id?: string;
  duration_s?: number;
}

export interface CookNextResponse {
  suggested_step_idx: number;
  actions: CookNextAction[];
  reason: string;
}

export async function fetchCookNext(sessionId: string): Promise<CookNextResponse> {
  return apiGet<CookNextResponse>(`/cook/session/${sessionId}/next`);
}

export function cookSessionEventsUrl(sessionId: string): string {
  const base = API_BASE.replace(/\/$/, "");
  return `${base}/cook/session/${sessionId}/events`;
}

export async function undoAdjustment(sessionId: string, adjustmentId: string): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/adjust/undo`, { adjustment_id: adjustmentId }, { idempotent: true });
}
