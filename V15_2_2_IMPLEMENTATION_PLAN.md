# v15.2.2 Implementation Plan: Gemini AutoFlow

## Goal
Replace dumb/stale autoflow with AI-driven "Next Best Action" that stays in sync with user progress during cooking.

## Backend Tasks

- [ ] **1. Schema Definition**
  - Define `AutoflowRequest` (step_index, mode, client_state).
  - Define `AutoflowSuggestion` (type, label, action, confidence, why).
  - Define `AutoflowResponse` (suggestions, source, autoflow_id).

- [ ] **2. Service Logic (`services/api/app/services/cook_autoflow.py`)**
  - Create new service file.
  - Implement heuristic fallbacks (fast).
  - Implement AI logic (Gemini) with specific rules:
    - No "Mark Complete" unless bullets checked AND (timer done OR no timer needed).
    - Suggest Timer only if `minutes_est >= 3`, no running timer, and progress started.
  - Implement caching (short TTL based on session state).

- [ ] **3. API Endpoint (`services/api/app/routers/cook.py`)**
  - Add `POST /session/{session_id}/autoflow`.
  - Validate session ownership.
  - Call service.

- [ ] **4. Tests (`services/api/tests/test_cook_autoflow_v15_2_2.py`)**
  - Test scenarios: empty state, bullets checked, timer running, timer done.
  - Verify caching behavior.

## Frontend Tasks

- [ ] **1. Hooks (`apps/web/src/features/cook/hooks.ts`)**
  - Add `useCookAutoflow` hook.
  - Integrate with `useCookSession` to react to `state_version`.

- [ ] **2. UI Component (`apps/web/src/features/cook/components/NextUpPanel.tsx`)**
  - Rework to consume autoflow suggestions.
  - Handle actions (timer create, bullet check, navigation).
  - Add responsiveness (optimistic UI, loading states).

## Verification
- Start step -> verify no spam.
- Check bullet -> verify timer suggestion.
- Start timer -> verify suggestion update.
- Timer done -> verify "complete step" suggestion.
