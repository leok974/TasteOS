/**
 * API client for TasteOS backend
 *
 * All functions automatically include authentication headers
 */

import type {
  Recipe,
  RecipeVariant,
  RecipeDiff,
  UserPlan
} from '@tasteos/types';
import { getAuthHeader } from './auth';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

/**
 * API error class
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Quota exceeded error - thrown when user hits daily variant limit
 */
export class QuotaExceededError extends ApiError {
  constructor(
    public plan: string,
    public used: number,
    public limit: number,
    message?: string
  ) {
    super(
      message || `You've used ${used}/${limit} variants on the ${plan} plan`,
      402,
      { plan, used, limit }
    );
    this.name = 'QuotaExceededError';
  }
}

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetails;
    try {
      errorDetails = await response.json();
    } catch {
      errorDetails = { detail: response.statusText };
    }

    throw new ApiError(
      errorDetails.detail?.message || errorDetails.detail || 'API request failed',
      response.status,
      errorDetails
    );
  }

  return response.json();
}

/**
 * Get a single recipe by ID
 */
export async function getRecipe(id: string): Promise<Recipe> {
  return apiRequest<Recipe>(`/api/v1/recipes/${id}`);
}

/**
 * Get all recipes for current user
 */
export async function getRecipes(): Promise<Recipe[]> {
  return apiRequest<Recipe[]>('/api/v1/recipes/');
}

/**
 * Generate a new variant for a recipe
 */
export async function generateVariant(
  recipeId: string,
  variantType: string,
  options: {
    dietary_restriction?: string;
    target_cuisine?: string;
    substitutions?: Record<string, string>;
  } = {}
): Promise<RecipeVariant> {
  try {
    return await apiRequest<RecipeVariant>('/api/v1/variants/generate', {
      method: 'POST',
      body: JSON.stringify({
        recipe_id: recipeId,
        variant_type: variantType,
        ...options,
      }),
    });
  } catch (error) {
    // Handle 402 quota exceeded specially
    if (error instanceof ApiError && error.statusCode === 402) {
      const detail = error.details?.detail;
      if (detail && typeof detail === 'object') {
        throw new QuotaExceededError(
          detail.plan || 'free',
          detail.used || 0,
          detail.limit || 0,
          detail.message
        );
      }
    }
    throw error;
  }
}

/**
 * Get all variants for a recipe
 */
export async function getRecipeVariants(recipeId: string): Promise<RecipeVariant[]> {
  return apiRequest<RecipeVariant[]>(`/api/v1/variants/recipe/${recipeId}`);
}

/**
 * Get diff between original recipe and variant
 */
export async function getVariantDiff(variantId: string): Promise<RecipeDiff> {
  return apiRequest<RecipeDiff>(`/api/v1/variants/${variantId}/diff`);
}

/**
 * Approve a variant
 */
export async function approveVariant(variantId: string): Promise<RecipeVariant> {
  return apiRequest<RecipeVariant>(`/api/v1/variants/${variantId}/approve`, {
    method: 'POST',
  });
}

/**
 * Get current billing plan and usage
 */
export async function getBillingPlan(): Promise<{
  plan: UserPlan;
  dailyVariantQuotaUsed: number;
  limits: {
    daily_variants: number;
    remaining: number;
  };
  subscription_status: string;
}> {
  return apiRequest('/api/v1/billing/plan');
}

/**
 * Create checkout session for upgrade
 */
export async function startCheckout(interval: "monthly" | "yearly"): Promise<{
  checkout_url: string;
  message?: string;
}> {
  return apiRequest('/api/v1/billing/checkout-session', {
    method: 'POST',
    body: JSON.stringify({ interval }),
  });
}

/**
 * Get customer portal URL
 */
export async function getBillingPortal(): Promise<{
  portal_url: string;
  message?: string;
}> {
  return apiRequest('/api/v1/billing/portal');
}

/**
 * Import recipe from URL
 */
export async function importRecipeFromUrl(url: string): Promise<Recipe> {
  const response = await apiRequest<{ recipe: Recipe; message: string }>(
    '/api/v1/imports/url',
    {
      method: 'POST',
      body: JSON.stringify({ url }),
    }
  );
  return response.recipe;
}

/**
 * Import recipe from image file
 */
export async function importRecipeFromImage(file: File): Promise<Recipe> {
  const formData = new FormData();
  formData.append('image', file);

  const headers = {
    ...getAuthHeader(),
    // Don't set Content-Type for FormData - browser will set it with boundary
  };

  const response = await fetch(`${API_BASE}/api/v1/imports/image`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorDetails;
    try {
      errorDetails = await response.json();
    } catch {
      errorDetails = { detail: response.statusText };
    }

    throw new ApiError(
      errorDetails.detail?.message || errorDetails.detail || 'Failed to import recipe from image',
      response.status,
      errorDetails
    );
  }

  const data: { recipe: Recipe; message: string } = await response.json();
  return data.recipe;
}

/**
 * Get nutrition information for a recipe
 */
export async function getRecipeNutrition(recipeId: string): Promise<{
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  notes: string | null;
}> {
  return apiRequest<{
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    notes: string | null;
  }>(`/api/v1/recipes/${recipeId}/nutrition`);
}

/**
 * Get nutrition information for a variant
 */
export async function getVariantNutrition(variantId: string): Promise<{
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  notes: string | null;
}> {
  return apiRequest<{
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    notes: string | null;
  }>(`/api/v1/variants/${variantId}/nutrition`);
}

/**
 * Pantry API Types and Functions
 */

export interface PantryItem {
  id: string;
  user_id: string;
  name: string;
  quantity: number | null;
  unit: string | null;
  expires_at: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface PantryItemCreate {
  name: string;
  quantity?: number;
  unit?: string;
  expires_at?: string;
  tags?: string[];
}

/**
 * Get all pantry items
 */
export async function getPantry(): Promise<PantryItem[]> {
  return apiRequest<PantryItem[]>('/api/v1/pantry/');
}

/**
 * Add a new pantry item
 */
export async function addPantryItem(data: PantryItemCreate): Promise<PantryItem> {
  return apiRequest<PantryItem>('/api/v1/pantry/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a pantry item
 */
export async function deletePantryItem(id: string): Promise<void> {
  await apiRequest<{ status: string; message: string }>(`/api/v1/pantry/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Parse pantry item from text or barcode
 */
export async function scanPantryItem(params: {
  barcode?: string;
  raw_text?: string;
}): Promise<{ draft_item: PantryItemCreate; message: string }> {
  const queryParams = new URLSearchParams();
  if (params.barcode) queryParams.append('barcode', params.barcode);
  if (params.raw_text) queryParams.append('raw_text', params.raw_text);

  return apiRequest<{ draft_item: PantryItemCreate; message: string }>(
    `/api/v1/pantry/scan?${queryParams}`,
    { method: 'POST' }
  );
}

/**
 * Meal Planner API Types and Functions
 */

export interface MealPlan {
  id: string;
  user_id: string;
  date: string;
  breakfast: Array<{ recipe_id: string; title: string }>;
  lunch: Array<{ recipe_id: string; title: string }>;
  dinner: Array<{ recipe_id: string; title: string }>;
  snacks: Array<{ recipe_id: string; title: string }>;
  total_calories: number | null;
  total_protein_g: number | null;
  total_carbs_g: number | null;
  total_fat_g: number | null;
  notes: string | null;
  plan_batch_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratePlanOptions {
  days: number;
  goals: {
    calories: number;
    protein_g: number;
  };
  dietary_preferences: string[];
  budget?: string;
}

export interface GeneratePlanResponse {
  plan_ids: string[];
  summary: string;
  start_date: string;
}

/**
 * Generate a meal plan
 */
export async function generateMealPlan(
  options: GeneratePlanOptions
): Promise<GeneratePlanResponse> {
  return apiRequest<GeneratePlanResponse>('/api/v1/planner/generate', {
    method: 'POST',
    body: JSON.stringify(options),
  });
}

/**
 * Get today's meal plan
 */
export async function getTodayPlan(): Promise<MealPlan> {
  return apiRequest<MealPlan>('/api/v1/planner/today');
}

/**
 * Get a specific meal plan by ID
 */
export async function getPlanById(planId: string): Promise<MealPlan> {
  return apiRequest<MealPlan>(`/api/v1/planner/${planId}`);
}

/**
 * Shopping List API Types and Functions
 */

export interface GroceryItem {
  id: string;
  user_id: string;
  meal_plan_id: string | null;
  name: string;
  quantity: number | null;
  unit: string | null;
  purchased: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Generate shopping list from a meal plan
 */
export async function generateShoppingList(planId: string): Promise<GroceryItem[]> {
  return apiRequest<GroceryItem[]>(`/api/v1/shopping/generate?plan_id=${planId}`, {
    method: 'POST',
  });
}

/**
 * Get all grocery items
 */
export async function getShoppingList(): Promise<GroceryItem[]> {
  return apiRequest<GroceryItem[]>('/api/v1/shopping/');
}

/**
 * Toggle purchased status of a grocery item
 */
export async function togglePurchased(itemId: string): Promise<GroceryItem> {
  return apiRequest<GroceryItem>(`/api/v1/shopping/${itemId}/toggle`, {
    method: 'POST',
  });
}

/**
 * Export shopping list as CSV
 */
export async function exportShoppingList(): Promise<string> {
  const headers = {
    ...getAuthHeader(),
  };

  const response = await fetch(`${API_BASE}/api/v1/shopping/export`, {
    method: 'POST',
    headers,
  });

  if (!response.ok) {
    throw new ApiError('Failed to export shopping list', response.status);
  }

  return response.text();
}

