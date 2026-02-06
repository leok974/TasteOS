# AI/LLM Feature Inventory

**Audit Date:** February 06, 2026
**Scope:** TasteOS Services API & Web Frontend

## Live Features (Gemini Powered)

### 1. Note Insights & Patterns
*   **UI Surface:** Plan Page & Recipe Detail (Insights Card)
*   **Provider:** Gemini 3 Flash Preview (`google.generativeai` V1 SDK)
*   **Endpoint:** `POST /api/insights/notes`
*   **Mechanism:** Analyzes user's note history to find cooking patterns.
*   **Guardrails:** Pydantic validation (`InsightsResponse`), Workspace scoped.
*   **Status:** **Live**, but uses older SDK. Falls back to heuristics if API key missing.

### 2. Cook Session Summary Polish
*   **UI Surface:** Cook Session Summary ("Polish with AI" Toggle)
*   **Provider:** Gemini 3 Flash Preview (`google.genai` V2 SDK)
*   **Endpoint:** `POST /api/cook/summary/polish`
*   **Mechanism:** Rewrites raw cooking logs and notes into a clean, concise summary.
*   **Guardrails:** Structured Output (JSON Schema), System Prompt controls.
*   **Status:** **Live**.

### 3. Recipe Image Generation
*   **UI Surface:** Ingest/Edit Recipe Modal
*   **Provider:** Gemini 3 Flash Image (or configured model) (`google.genai` V2 SDK)
*   **Endpoint:** `POST /api/recipes/{id}/image`
*   **Mechanism:** Generates food photography based on recipe title and cuisine.
*   **Status:** **Live**.

### 4. Cook Adjustments (Assist)
*   **UI Surface:** Cook Mode -> Adjust Recipe / "Assist" Panel
*   **Provider:** Gemini 3 Flash Preview (`google.genai` V2 SDK)
*   **Endpoint:** `POST /api/cook/adjust`
*   **Mechanism:** Suggests modifications (timers, ingredient scaling) based on user query.
*   **Status:** **Live**.

## Stubbed / Heuristic Features (Action Required)

### 1. Recipe Nutrition Analysis ("Analyze" Button)
*   **UI Surface:** Recipe Detail View Header
*   **Endpoint:** `POST /api/ai/macros`
*   **Status:** **STUB**.
*   **Current Logic:** `services/ai_service.py` returns hardcoded mock data based on simple keyword matching (e.g., "salad" -> low calorie, "steak" -> high protein).
*   **Recommendation:** High priority to wire to Gemini to provide real nutritional estimates.

### 2. Ingredient Substitutions
*   **UI Surface:** Ingredient Row Actions (via `useSubstitute` hook)
*   **Endpoint:** `POST /api/ai/substitute`
*   **Status:** **STUB**.
*   **Current Logic:** `services/ai_service.py` returns minimal hardcoded suggestions (e.g., buttermilk -> milk+vinegar).
*   **Recommendation:** Wire to Gemini to leverage pantry awareness for smart substitutions.

## Architecture Findings

*   **SDK Inconsistency:** The codebase mixes `google.generativeai` (older V1 SDK, used in Insights) and `google.genai` (newer V2 SDK, used in Images/Cook).
*   **No Unified Wrapper:** Each service instantiates its own client. A centralized provider (e.g., `app.core.ai_client`) allows better monitoring, rate limiting, and config management.
*   **Mock Mode:** `AI_MODE="mock"` is supported but disparate implementation across services.
