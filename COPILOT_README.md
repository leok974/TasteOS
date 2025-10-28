# Copilot / MCP Usage Policy

This document defines strict operational policies for AI agents (GitHub Copilot, Claude, etc.) working with TasteOS via Model Context Protocol (MCP) servers.

## Core Principles

1. **Security First**: Never expose secrets, tokens, or credentials in logs or chat
2. **Reproducibility**: All tests must be automated and logged for review
3. **Isolation**: Services run in dedicated terminals with proper lifecycle management
4. **Whitelisting**: Only pre-approved commands and paths are accessible via MCP

---

## MCP Servers

### Available Servers

- **`tasteos-shell`**: Executes whitelisted commands from `apps/api/scripts/`
- **`tasteos-logs`**: Provides read-only access to `LOGS/*.txt` files

### Server Restrictions

- Shell server only allows: `test_api.ps1`, `test_api.sh`, `login.ps1`
- Filesystem server only reads `.txt` files from `LOGS/` directory
- No parent directory traversal (`..`) or absolute paths allowed
- All paths are validated against workspace root: `D:\TasteOS`

### Testing MCP Servers

Before using MCP servers in workflows, validate they're working:

```powershell
cd .mcp
npm run mcp:shell:probe   # Check shell server + script whitelist
npm run mcp:logs:probe     # Check logs server + LOGS/ access
```

Expected output:
```
✓ TasteOS Shell MCP Server ready
  Workspace: D:\TasteOS
  Scripts: D:\TasteOS\apps\api\scripts
  ✓ test_api.ps1
  ✓ test_api.sh
  ✓ login.ps1
```

---

## Service Management

### Starting the API

**DO NOT** run `uvicorn` manually in an interactive terminal.

**Correct approach:**
1. Use VS Code task: `Ctrl+Shift+P` → "Run Task" → `api:dev`
2. Or via shell MCP: Request execution of whitelisted start command
3. The API runs in a dedicated background terminal

**Why**: Manual terminal usage breaks reproducibility and makes it hard to track service state.

### Service Lifecycle

- Each service (API, web, app) runs in its own terminal
- Do not kill or reuse service terminals
- Use VS Code tasks for clean start/stop: `api:dev`, `web:dev`, `app:dev`

---

## Smoke Testing Workflow

### Standard Smoke Test Flow

1. **Get Token**:
   ```powershell
   # Via login script (whitelisted)
   .\apps\api\scripts\login.ps1
   # Output: TASTEOS_TOKEN=***REDACTED*** (length: 187)
   # Token stored in $env:TASTEOS_TOKEN
   ```

2. **Run Smoke Tests**:
   ```powershell
   # Via test script (whitelisted) with logging
   .\apps\api\scripts\test_api.ps1 -Token $env:TASTEOS_TOKEN -SaveLog
   # Output: ✓ Log saved to: D:\TasteOS\LOGS\smoke_2025-10-28T14-30-45.txt
   ```

3. **Read Results**:
   - Use `tasteos-logs` MCP server to read the generated log file
   - Example: `@tasteos-logs smoke_2025-10-28T14-30-45.txt`

4. **Analyze & Fix**:
   - Inspect `/auth/me` and `/recipes/` responses in log
   - Identify errors (401, 422, UUID issues, etc.)
   - Propose code fixes in `apps/api/tasteos_api/`
   - Rerun smoke tests to verify

### Automated Debug Loop

```
[Copilot] → [MCP Shell: login.ps1] → $env:TASTEOS_TOKEN
         → [MCP Shell: test_api.ps1 -SaveLog] → LOGS/smoke_<timestamp>.txt
         → [MCP Logs: read smoke file] → Analyze results
         → [Propose fixes] → [Edit code] → [Repeat]
```

This creates a **reproducible, auditable testing workflow** where every test run is logged and traceable.

---

## Secrets Management

### Never Print Raw Secrets

**FORBIDDEN**:
- JWT tokens in full (e.g., `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)
- Stripe API keys (`sk_test_...`, `pk_live_...`)
- Database URLs with credentials
- OpenAI API keys (`sk-...`)
- Any password or sensitive string

**Correct Reference**:
- `[REDACTED_TOKEN]`
- `***REDACTED*** (length: 187)`
- `Bearer ***REDACTED***`

### Script Token Handling

All whitelisted scripts **must** redact tokens before output:

- **`login.ps1`**: Prints `TASTEOS_TOKEN=***REDACTED***`, stores real token in `$env:TASTEOS_TOKEN` and `.mcp/scratch/token.local.txt`
- **`test_api.ps1`**: Logs show `Token: ***REDACTED*** (length 187)`, not the full bearer token

### Log File Security

- Log files in `LOGS/*.txt` must have tokens redacted
- Never commit logs to version control (covered by `.gitignore`)
- If a log accidentally contains secrets, delete it and regenerate

---

## Code Editing Policies

### Allowed Edits

You may read/write files in these directories:
- `apps/api/tasteos_api/**` (backend logic)
- `apps/web/src/**` (Next.js frontend)
- `apps/app/src/**` (Tauri app)
- `packages/**` (shared libraries)
- `tests/e2e/**` (Playwright tests)

### Edit-Test Cycle

1. **Identify Issue**: Read smoke test log via `tasteos-logs` MCP
2. **Propose Fix**: Edit relevant files (e.g., `tasteos_api/routers/auth.py`)
3. **Verify**: Rerun smoke tests via `tasteos-shell` MCP
4. **Iterate**: Repeat until tests pass

### Restricted Operations

- **NO**: Reading outside workspace root
- **NO**: Writing to `LOGS/` (tests write logs, agent only reads)
- **NO**: Modifying `.mcp/` servers (they're locked configuration)
- **NO**: Editing `package.json` dependencies without explicit user approval

---

## Log Access

### Reading Logs

- Only read logs via `tasteos-logs` MCP server
- Only `.txt` files in `LOGS/` directory are accessible
- Use helper script to find latest: `.\scripts\print-latest-smoke.sh`

### Log Contents

Logs typically contain:
- Test execution timestamps
- HTTP request/response details (status, body, headers)
- Redacted tokens (`***REDACTED***`)
- Error messages and stack traces

### Security Constraints

**Never attempt to read**:
- Files outside `LOGS/` directory
- Database files (`.db`, `.sqlite`)
- Environment files (`.env`, `.env.local`)
- Migration dumps or JSON exports
- Token scratch files (`.mcp/scratch/token.local.txt`)

---

## Best Practices

### Before Starting Work

1. **Check Service Status**: Ensure API is running via `api:dev` task
2. **Validate MCP**: Run probe scripts (`npm run mcp:shell:probe`)
3. **Get Fresh Token**: Run `login.ps1` to populate `$env:TASTEOS_TOKEN`

### During Development

1. **Small Iterations**: Make one focused change at a time
2. **Test After Each Change**: Run smoke tests to verify fixes
3. **Read Logs**: Always read the generated log file to confirm behavior
4. **Document Issues**: Note any patterns in failures (UUID, auth, CORS, etc.)

### After Completing Work

1. **Verify All Tests Pass**: Final smoke test should show all ✓ SUCCESS
2. **Clean Up**: Remove any temporary test data if needed
3. **Check Logs**: Ensure no secrets leaked into log files

---

## Common Issues & Solutions

### 401 Unauthorized

**Cause**: Token expired or invalid
**Fix**: Run `login.ps1` to get fresh token, then retry tests

### UUID Conversion Errors

**Cause**: JWT stores user ID as string, database expects UUID
**Fix**: Add `UUID(user_id_str)` conversion in `core/dependencies.py`

### 307 Redirect (Lost Authorization Header)

**Cause**: FastAPI trailing slash redirect strips headers
**Fix**: Always use trailing slash on routes: `/recipes/`, not `/recipes`

### Bcrypt Password Length

**Cause**: Bcrypt only supports 72-byte passwords
**Fix**: Truncate in `auth.py`: `password[:72]` before hashing

### Circular Import

**Cause**: `routers/auth.py` and `routers/recipes.py` importing each other
**Fix**: Move shared dependencies (e.g., `get_current_user`) to `core/dependencies.py`

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────┐
│                    Copilot Workflow                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Start API        → VS Code Task: api:dev           │
│  2. Login            → @tasteos-shell login.ps1         │
│  3. Smoke Test       → @tasteos-shell test_api.ps1      │
│  4. Read Log         → @tasteos-logs smoke_<time>.txt   │
│  5. Analyze Results  → Inspect JSON responses           │
│  6. Fix Code         → Edit tasteos_api/**/*.py        │
│  7. Repeat 3-6       → Until all tests pass             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## API Contracts (Phase 1 - BLESSED)

The following API shapes are **locked and production-ready**. Do not modify without explicit approval.

### Billing Plan Endpoint

**Request:**
```
GET /api/v1/billing/plan
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "plan": "free",
  "dailyVariantQuotaUsed": 2,
  "limits": {
    "daily_variants": 3,
    "remaining": 1
  },
  "subscription_status": "active"
}
```

**Fields:**
- `plan`: `"free"` | `"pro"` | `"enterprise"`
- `dailyVariantQuotaUsed`: Number of variants generated today (integer)
- `limits.daily_variants`: Daily quota for user's plan (integer)
- `limits.remaining`: Variants remaining today (integer, calculated as `daily_variants - dailyVariantQuotaUsed`)
- `subscription_status`: `"active"` | `"canceled"` | `"past_due"` | `"unpaid"` | `"trialing"`

### Variant Generation Quota Error

**Request:**
```
POST /api/v1/variants/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "recipe_id": "uuid-here",
  "variant_type": "dietary"
}
```

**Response (402 - Quota Exceeded):**
```json
{
  "detail": {
    "message": "Daily variant generation limit reached. Please upgrade to continue.",
    "plan": "free",
    "used": 3,
    "limit": 3
  }
}
```

**Fields:**
- `detail.message`: Human-readable error message (string)
- `detail.plan`: Current plan of user (string)
- `detail.used`: Number of variants already generated today (integer)
- `detail.limit`: Daily quota for user's plan (integer)

**Frontend Handling:**
```typescript
try {
  const variant = await generateVariant(recipeId, variantType);
} catch (err) {
  if (err instanceof ApiError && err.statusCode === 402) {
    // Show PlanGuard upsell component
    // Display: "You've used {used}/{limit} variants on the {plan} plan"
  }
}
```

### Daily Quota Limits (Backend Constants)

**Location:** `apps/api/tasteos_api/core/quotas.py`

```python
DAILY_VARIANT_QUOTAS = {
    "free": 3,
    "pro": 30,
    "enterprise": 60,
}
```

**Frontend Constants:** `apps/app/src/lib/planLimits.ts`

```typescript
export const PLAN_LIMITS = {
  free: { dailyVariantQuota: 3 },
  pro: { dailyVariantQuota: 30 },
  enterprise: { dailyVariantQuota: 60 },
}
```

### Contract Enforcement

- **Backend**: `apps/api/tasteos_api/routers/variants.py` calls `check_variant_quota()` before generation
- **Frontend**: `apps/app/src/components/VariantPanel.tsx` calls `getBillingPlan()` and uses `canGenerateVariant()` to show/hide PlanGuard
- **Database**: `variant_usage` table logs every generation event with `user_id`, `recipe_id`, `variant_type`, `created_at`

These contracts are production-stable as of Phase 1 completion (2025-10-28).

---

## Version History

- **2025-10-28**: Initial policy (MCP shell/logs servers, smoke test flow)
- **2025-10-28**: Added Phase 1 API contracts (billing/plan, quota 402 error)

---

**Follow this document, not vibes.** These policies ensure security, reproducibility, and maintainability of the TasteOS development workflow.
