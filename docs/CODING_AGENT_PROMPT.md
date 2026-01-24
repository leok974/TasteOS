# Coding Agent Prompt — TasteOS build (MVP)

You are implementing the TasteOS monorepo. Use safe, incremental commits and keep tests green.

## Hard constraints
1) **Monorepo** structure already scaffolded. Do not rename directories.
2) Keep **API contract stable** (`/api/ready`, `/api/recipes`).
3) **AI provider is Gemini** (Nano Banana image model). Use `google-genai` SDK.
4) Image storage must be **S3-compatible** (supports MinIO in dev, R2 or S3 in prod).
5) Every feature change includes tests:
   - API: `pytest`
   - Web: `vitest` (component) or Playwright later
6) No paid/cloud calls in CI: default to `AI_MODE=mock` for tests.

## Current status (what exists)
- `services/api`:
  - FastAPI app with recipes table (auto-created on startup)
  - `POST /api/recipes` creates recipe and (optionally) generates & uploads a PNG
  - `AI_MODE=mock` returns a dummy image (no Gemini call)
  - S3-compatible uploader via boto3
- `apps/web`:
  - Next.js renders the prototype UI with amber color system
  - Cook Mode overlay includes **step cards + a vertical timeline** (DP timeline style)
  - Method selection shows a **single-row tradeoff summary**

## Next deliverables (implement in order)
### 1) Wire web to API (vertical slice)
- Add a minimal `Recipes` view that:
  - lists `/api/recipes`
  - allows creating a recipe (title + cuisine)
  - displays `image_url` if present; otherwise show placeholder
- Add `vitest` coverage for the new API client hook/component.

### 2) Real image generation toggle (safe)
- Add a UI setting for `AI_MODE` display only (do not expose secrets).
- In dev: user can run API with `AI_MODE=gemini` + `GEMINI_API_KEY`.

### 3) Storage correctness + docs
- Add docs showing:
  - MinIO local usage
  - R2 env vars (endpoint + bucket + keys)
  - public base URL usage
- Add an API healthcheck endpoint for object store (`/api/storage/health`) and tests (mocked).

### 4) Recipe card image caching policy
- When a recipe already has `image_url`, never regenerate unless explicitly requested.
- Add `POST /api/recipes/{id}/regenerate-image` (admin/dev-only for now) + test.

## UI target
The user will paste the existing canvas prototype code as the style target.
Keep the UI:
- warm neutral background (#FAF9F6)
- amber accents (chips, borders, CTA)
- rounded cards (2xl+) and soft shadows

