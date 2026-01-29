# v3.2.2 Completion Notes: Use Soon Autofill

## Status: Verified & Complete

### Features Implemented
1.  **Backend Analysis Engine (`autofill.py`)**:
    *   `generate_use_soon_proposals`: Scans pantry for expiring items, finds matching recipes, and scores them based on urgency and constraints.
    *   `apply_proposals`: Updates meal plan entries with selected recipes.
    *   **Logic**: Uses fuzzy matching (ILIKE) for ingredients and simple scoring heuristic (expiry date, match count).

2.  **API Endpoints (`routers/plan.py`)**:
    *   `POST /autofill/use-soon`: Generates proposals.
    *   `POST /autofill/use-soon/apply`: Commits changes to the database.

3.  **Frontend Experience (`UseSoonAutofillCard.tsx`)**:
    *   New card in the Plan dashboard.
    *   Displays proposals with "Why" tags (e.g., "Uses Milk", "Expires in 2d").
    *   Allows user to select/deselect specific swaps.
    *   Updates the plan via mutation.

### Verification
*   **Integration Testing**: Validated using `test_autofill_flow.py` (script deleted after success).
*   **Bug Fixes**:
    *   Fixed `AttributeError: type object 'Recipe' has no attribute 'deleted_at'`.
    *   Fixed SQLAlchemy `or_` import and syntax.
    *   Fixed `MealPlanEntry` join logic in `apply` endpoint.
    *   Corrected API path mismatch in `api.ts`.

### Next Steps
*   User acceptance testing.
*   Consider weighting "use soon" items by quantity (currently just existence).
