# TasteOS Development Workflow

This document describes the secure, reproducible workflow for developing and testing TasteOS.

## Architecture

The workflow uses three key components:

1. **VS Code Tasks** - Long-running services (API, web, app servers)
2. **Test Scripts** - Smoke tests and authentication helpers
3. **MCP Servers** - Secure, whitelisted command execution and log access

## Running Services

### Start the API Server
Use VS Code Task: **Terminal → Run Task → api:dev**

Or manually:
```bash
cd apps/api
.\venv\Scripts\Activate.ps1
python -m uvicorn tasteos_api.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Web App (Next.js)
Use VS Code Task: **Terminal → Run Task → web:dev**

Or manually:
```bash
pnpm dev:web
```

### Start the Dashboard (Vite)
Use VS Code Task: **Terminal → Run Task → app:dev**

Or manually:
```bash
pnpm dev:app
```

## Testing the API

### 1. Get an Authentication Token

**Using the helper script:**
```powershell
cd apps/api
.\scripts\login.ps1
```

This will output a JWT token. Copy it for use in tests.

**Or via MCP:**
```
"Use tasteos-shell to run pwsh -File apps/api/scripts/login.ps1"
```

### 2. Run Smoke Tests

**PowerShell:**
```powershell
cd apps/api
.\scripts\test_api.ps1 -Token "YOUR_TOKEN_HERE"
```

**Save output to logs:**
```powershell
.\scripts\test_api.ps1 -Token "YOUR_TOKEN_HERE" | Tee-Object ..\..\LOGS\smoke_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').txt
```

**Bash:**
```bash
cd apps/api
./scripts/test_api.sh "YOUR_TOKEN_HERE"
```

**Via MCP (recommended):**
```
"Use tasteos-shell to run pwsh -File apps/api/scripts/test_api.ps1 with args -Token 'YOUR_TOKEN'"
```

### 3. Review Test Results

**List all log files:**
```
"Use tasteos-logs to list all log files"
```

**Read a specific log:**
```
"Use tasteos-logs to read smoke_2025-10-28_final.txt"
```

## Security Features

### Whitelisted Commands (tasteos-shell MCP)
Only these commands can be executed:
- `pwsh -File apps/api/scripts/test_api.ps1`
- `bash apps/api/scripts/test_api.sh`
- `pwsh -File apps/api/scripts/login.ps1`
- `pnpm dev:api/dev:web/dev:app`
- `pnpm typecheck/lint/test`

Any other command will be rejected.

### Restricted Filesystem Access (tasteos-logs MCP)
- **Read-only access** to `LOGS/` directory
- Cannot access files outside LOGS/
- Cannot write or delete files

## Workflow Best Practices

### When Developing
1. Start API server with VS Code task `api:dev` in dedicated terminal
2. Make code changes
3. Server auto-reloads on file changes
4. Run smoke tests via MCP to verify changes
5. Check logs via MCP to debug issues

### When Debugging Auth Issues
1. Get fresh token: `"Use tasteos-shell to run login script"`
2. Run smoke tests: `"Use tasteos-shell to run test_api.ps1 with token"`
3. Review logs: `"Use tasteos-logs to read latest log"`
4. Fix code based on log output
5. Repeat

### Capturing Evidence
All test outputs should be saved to `LOGS/` with timestamps:
```powershell
.\scripts\test_api.ps1 -Token $token | Tee-Object ..\..\LOGS\smoke_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').txt
```

Never commit actual log files (they may contain tokens).

## API Endpoints

All endpoints are prefixed with `/api/v1` and require trailing slashes:

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/me` - Get current user profile (requires auth)

### Recipes
- `GET /api/v1/recipes/` - List recipes (requires auth)
- `POST /api/v1/recipes/` - Create recipe (requires auth)
- `GET /api/v1/recipes/{id}` - Get single recipe
- `PATCH /api/v1/recipes/{id}` - Update recipe (requires auth, owner only)
- `DELETE /api/v1/recipes/{id}` - Delete recipe (requires auth, owner only)

### Interactive Docs
Open http://127.0.0.1:8000/docs for Swagger UI

## Variant Generation 🎉

### Quick Start

```powershell
# 1. Get token
.\apps\api\scripts\login.ps1

# 2. Test variants
.\apps\api\scripts\test_variant.ps1 -Token $env:TASTEOS_TOKEN

# 3. See quickstart guide
.\apps\api\scripts\variant-quickstart.ps1
```

### Supported Variant Types

- **dietary** - vegetarian, vegan, gluten-free, keto, etc.
- **cuisine** - Italian → Mexican, Asian → Mediterranean, etc.
- **ingredient_substitution** - Replace specific ingredients
- **simplify** - Reduce complexity for weeknight cooking
- **upscale** - Premium ingredients and techniques

### API Endpoints

```
POST   /api/v1/variants/generate           Generate new variant
GET    /api/v1/variants/{id}               Get variant details
GET    /api/v1/variants/recipe/{recipe_id} List all variants
POST   /api/v1/variants/{id}/approve       Approve variant
GET    /api/v1/variants/{id}/diff          Show changes
```

**📖 Full documentation:** VARIANT_GENERATION_COMPLETE.md

## Troubleshooting

### "Not authenticated" errors
- Check token hasn't expired (24 hour expiration)
- Ensure using trailing slash on recipe endpoints (`/recipes/` not `/recipes`)
- Verify Authorization header format: `Bearer <token>`

### Server won't start
- Check if port 8000 is already in use
- Verify Python virtual environment is activated
- Check server logs for import errors

### Tests fail with 500 errors
- Check server terminal for Python traceback
- Review `LOGS/` output for request/response details
- Verify database file exists at `apps/api/tasteos.db`

## Next Steps

### ✅ Completed Features

- [x] User authentication (register, login, token refresh)
- [x] Recipe CRUD operations
- [x] JWT-based authorization
- [x] MCP-based secure workflow
- [x] **AI variant generation with LangGraph**
- [x] **Stripe billing integration with usage tracking**

### 🎯 Next Priorities

1. **Frontend Implementation**
   - Authentication forms (login, register)
   - Recipe management UI (create, edit, list)
   - Variant generation interface
   - Usage dashboard and upgrade prompts
   - Stripe Checkout integration

2. **Recipe import with AI**
   - URL scraping and parsing
   - Image-to-recipe OCR
   - Format normalization
   - Ingredient recognition

3. **Polish & Testing**
   - E2E tests with Playwright
   - Error handling improvements
   - Performance optimization
   - API documentation

