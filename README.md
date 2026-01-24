# TasteOS (monorepo)

Agentic cooking app: family recipe sharing, smart categorization, pantry-aware cooking, weekly planning, and Gemini “Nano Banana” recipe card images.

## Repo layout

- `apps/web` — Next.js (App Router) + TypeScript + Tailwind + shadcn-style UI
- `services/api` — FastAPI + Postgres + Gemini image generation + S3-compatible object store (Cloudflare R2 / MinIO / AWS S3)

## Quickstart (Docker + local web)

1) Copy env:
```bash
cp .env.example .env
```

2) Start dependencies + API:
```bash
docker compose -f infra/docker-compose.dev.yml up --build
```

3) Start web locally (recommended):
```bash
cd apps/web
pnpm i
pnpm dev
```

Open http://localhost:3000

### API
- http://localhost:8000/api/ready
- http://localhost:8000/api/docs

## Object storage

Local dev uses MinIO (S3-compatible):
- Console: http://localhost:9001 (minioadmin/minioadmin)
- Public base URL: http://localhost:9000/tasteos-images

Prod can use Cloudflare R2 or AWS S3 by updating the `OBJECT_*` env vars.
