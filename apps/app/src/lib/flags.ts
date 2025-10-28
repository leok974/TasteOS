/**
 * Feature flags for TasteOS application
 *
 * Controls visibility of Phase 3 features (Pantry, Planner, Shopping)
 */

/**
 * Check if Pantry feature is enabled
 */
export function isPantryEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_PANTRY === "1";
}

/**
 * Check if Meal Planner feature is enabled
 */
export function isPlannerEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_PLANNER === "1";
}

/**
 * Check if Shopping feature is enabled (depends on Planner)
 */
export function isShoppingEnabled(): boolean {
  return isPlannerEnabled(); // Shopping requires planner
}
