
# v15.3.2 Completion Notes: Recipe Insights Persistence

## Status: Verified & Complete

### Features Implemented
1.  **Database Persistence**:
    *   Added `RecipeMacroEntry` and `RecipeTipEntry` models in `models.py`.
    *   Linked to `Recipe` (though strictly loose coupling via ID).
    *   Track `source` (user, ai, heuristic) and `confidence`.

2.  **API Endpoints (`routers/recipes.py`)**:
    *   `GET /recipes/{id}/macros`: Returns latest saved estimation.
    *   `POST /recipes/{id}/macros`: Start manual save or overwrite.
    *   `POST /recipes/{id}/macros/estimate`: Generates estimate (AI/Heuristic), optionally persists.
    *   `GET /recipes/{id}/tips`: Returns latest tips for scope (storage/reheat).
    *   `POST /recipes/{id}/tips/estimate`: Generates tips (AI/Heuristic), optionally persists.

3.  **Honest AI Logic**:
    *   The `estimate` endpoints respect the `source` returned by AI service.
    *   If AI fails or returns he
# v15.3.2 Completion Notes: Recipe Insrce
## Status: Verified & Complete

### Features Implemenwit
### Features Implemented
1. cat1.  **Database Persiste C    *   Added `RecipeMacroEte    *   Linked to `Recipe` (though strictly loose coupling via ID).
    *   Trah     *   Track `source` (user, ai, heuristic) and `confidence`.

He
2.  **API Endpoints (`routers/recipes.py`)**:
    *   `GET /rech    *   `GET /recipes/{id}/macros`: Returns d     *   `POST /recipes/{id}/macros`: Start manual save or overwrite      *   `POST /recipes/{id}/macros/estimate`: Generates estimate (Ais    *   `GET /recipes/{id}/tips`: Returns latest tips for sco
