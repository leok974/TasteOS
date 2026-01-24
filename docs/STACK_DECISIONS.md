# Stack decisions (MVP)

## Monorepo
- `apps/web` (Next.js) + `services/api` (FastAPI)
- Rationale: one repo, one set of CI checks, easy local dev.

## AI provider
- Gemini “Nano Banana” image generation (`gemini-2.5-flash-image`) for recipe card images. citeturn1view0

## Storage (generated images)
We implement **S3-compatible** uploads so we can choose between:
- **Cloudflare R2** (recommended for *lowest cost* for images: free tier + no egress fees in many cases). citeturn0search11
- **AWS S3** (easy to scale + deep ecosystem, but egress costs can bite for image-heavy apps).

MVP default:
- Local dev: MinIO
- Prod: R2 (or S3) by setting env vars

## Compute / hosting
Defer decision until the app works end-to-end.

When we deploy:
- If optimizing cost: Cloudflare (Pages/Workers) or a small VPS + R2
- If optimizing AWS learning + ecosystem: ECS/Fargate (or EC2) + S3

