/**
 * TasteOS API Client
 * 
 * Fetches from the FastAPI backend at /api/*
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

// --- Types ---

let currentWorkspaceId: string | null = null;

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
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `GET ${path} failed: ${res.status}`);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `POST ${path} failed: ${res.status}`);
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
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `PATCH ${path} failed: ${res.status}`);
  }
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `DELETE ${path} failed: ${res.status}`);
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
  return apiPost<Recipe>('/recipes', data);
}

export async function updateRecipe(id: string, data: Partial<RecipeCreateInput>): Promise<Recipe> {
  return apiPatch<Recipe>(`/recipes/${id}`, data);
}

export async function seedDevData(): Promise<SeedResponse> {
  return apiPost<SeedResponse>('/dev/seed');
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
  return apiPost<ImageGenerateResponse>(`/recipes/${recipeId}/image/generate`);
}

export async function regenerateImage(recipeId: string): Promise<ImageGenerateResponse> {
  return apiPost<ImageGenerateResponse>(`/recipes/${recipeId}/image/regenerate`);
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
  return apiPost<ImportResult>(`/recipes/import?${query.toString()}`, payload);
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
  source: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export type CreatePantryItem = Omit<PantryItem, "id" | "workspace_id" | "created_at" | "updated_at">;
export type UpdatePantryItem = Partial<CreatePantryItem>;

export async function fetchPantryItems(params?: { search?: string; useSoon?: boolean }): Promise<PantryItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("q", params.search);
  if (params?.useSoon) searchParams.set("use_soon", "1");

  return apiGet<PantryItem[]>(`/pantry/?${searchParams.toString()}`);
}

export async function createPantryItem(item: CreatePantryItem): Promise<PantryItem> {
  return apiPost<PantryItem>("/pantry/", item);
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
}

export interface GroceryList {
  id: string;
  source?: string;
  created_at: string;
  items: GroceryListItem[];
}

export async function generateGroceryList(params: { recipeIds?: string[]; planId?: string }): Promise<GroceryList> {
  return apiPost<GroceryList>("/grocery/generate", { recipe_ids: params.recipeIds || [], plan_id: params.planId });
}

export async function fetchCurrentGroceryList(): Promise<GroceryList> {
  return apiGet<GroceryList>("/grocery/current");
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
  step_index: number;
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
  return apiPost<MethodPreviewResponse>(`/cook/session/${sessionId}/method/preview`, { method_key: methodKey });
}

export async function applyCookMethod(sessionId: string, methodKey: string, steps: RecipeStep[], tradeoffs: any): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/method/apply`, {
    method_key: methodKey,
    steps_override: steps,
    method_tradeoffs: tradeoffs
  });
}

export async function resetCookMethod(sessionId: string): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/method/reset`);
}

export async function apiPatchSession(sessionId: string, patch: any): Promise<CookSession> {
  return apiPatch<CookSession>(`/cook/session/${sessionId}`, patch);
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
  return apiPost<AdjustPreviewResponse>(`/cook/session/${sessionId}/adjust/preview`, req);
}

export async function applyAdjustment(
  sessionId: string,
  req: AdjustApplyRequest
): Promise<CookSession> {
  return apiPost<CookSession>(`/cook/session/${sessionId}/adjust/apply`, req);
}

