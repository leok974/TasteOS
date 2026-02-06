# Recommended AI Roadmap (Gemini)

Based on the [Audit](./LLM_INVENTORY.md) performed on Feb 06, 2026.

## Tier 1: Immediate Wins (Fixing Stubs)

These features already exist in the UI but are powered by "dumb" heuristics. Wiring them to Gemini provides immediate value without new UI work.

### 1. Real Recipe Nutrition Analysis ("Analyze" Button)
*   **Current State:** Returns mock ranges based on "steak" vs "salad" in title.
*   **Implementation Plan:**
    *   **Endpoint:** Update `POST /api/ai/macros` in `services/api/app/routers/ai.py`.
    *   **Logic:** Send full ingredient list + title to Gemini 3 Flash.
    *   **Prompt:** Ask for calorie range, protein, relevant health tags (e.g. "High Fiber", "Keto-friendly"), and a 1-sentence disclaimer.
    *   **Output:** `MacroAnalysis` (already defined in `ai_service.py`, just needs real data).
    *   **Cache:** Redis (TTL: 7 days). Key: `macros:{recipe_hash}`.

### 2. Context-Aware Ingredient Substitutions
*   **Current State:** Hardcoded checks for "buttermilk" and "egg".
*   **Implementation Plan:**
    *   **Endpoint:** Update `POST /api/ai/substitute` in `services/api/app/routers/ai.py`.
    *   **Logic:** Send `ingredient_to_replace`, `recipe_context` (title/cuisine), and `available_pantry_items`.
    *   **Prompt:** "Suggest the best substitute for {ingredient} in a {context} using only {pantry_items}. Explain why."
    *   **Output:** `SubstitutionSuggestion` (confidence, instruction, pantry_match).
    *   **Cache:** Redis (TTL: 24h).

### 3. Unified AI Client & SDK Migration
*   **Current State:** Mixed usage of `google.generativeai` and `google.genai`.
*   **Implementation Plan:**
    *   Create `services/api/app/core/ai.py` returning a configured singleton client.
    *   Migrate `InsightsGenerator` to use the V2 `google.genai` SDK.
    *   Ensure consistent valid JSON enforcement and error handling.

## Tier 2: High Value Additions

### 1. Smart Grocery List "Why"
*   **Idea:** When a user removes an item or sees a suggested addition, explain *why* based on their cooking history/pantry.
*   **Endpoint:** `POST /api/grocery/explain`
*   **Ref:** "Grocery list explanations (why skipped/reduced + “include anyway” guidance)"

### 2. Auto-Tagging on Ingest
*   **Idea:** When parsing a scraped recipe, use Gemini to apply canonical tags (Cuisine, Main Ingredient, Diet, Course).
*   **Endpoint:** Hook into `POST /api/recipes/ingest`.
*   **Benefit:** Improves searchability and Insights accuracy instantly.

### 3. Unit Conversion "Assistant"
*   **Idea:** If a user tries a cross-type conversion (mass <-> volume) without a density, assume context from recipe title and suggest the likely density or correct unit.
*   **Endpoint:** Extend `POST /api/units/convert` with `allow_ai_estimation=True`.

## Tier 3: Exploration

*   **Cook Mode "Ask about this step":** Contextual chatbot for the active step.
*   **Recipe Personalization:** Rewrite instructions to match user's equipment (e.g., "Air Fry" instead of "Deep Fry").
