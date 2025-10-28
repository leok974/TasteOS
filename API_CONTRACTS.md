# API Contracts - Quick Reference

**Status:** 🔒 BLESSED (Production-Stable as of Phase 1)  
**Last Updated:** 2025-10-28

---

## GET /api/v1/billing/plan

Get user's current plan and daily quota usage.

### Request
```http
GET /api/v1/billing/plan
Authorization: Bearer <token>
```

### Response (200 OK)
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

### Fields
| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `plan` | string | `"free"` \| `"pro"` \| `"enterprise"` | User's subscription plan |
| `dailyVariantQuotaUsed` | integer | `0..n` | Variants generated today (resets at midnight UTC) |
| `limits.daily_variants` | integer | `3` \| `30` \| `60` | Total daily quota for plan |
| `limits.remaining` | integer | `0..n` | Calculated: `daily_variants - dailyVariantQuotaUsed` |
| `subscription_status` | string | `"active"` \| `"canceled"` \| `"past_due"` \| `"unpaid"` \| `"trialing"` | Subscription state |

### Usage
```typescript
const plan = await getBillingPlan();
const canGenerate = canGenerateVariant(plan.plan, plan.dailyVariantQuotaUsed);
```

---

## POST /api/v1/variants/generate (Quota Error)

When user exceeds daily variant generation quota.

### Request
```http
POST /api/v1/variants/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "recipe_id": "550e8400-e29b-41d4-a716-446655440000",
  "variant_type": "dietary",
  "dietary_restriction": "vegetarian"
}
```

### Response (402 Payment Required)
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

### Fields
| Field | Type | Description |
|-------|------|-------------|
| `detail.message` | string | Human-readable error message for display |
| `detail.plan` | string | User's current plan (`"free"` \| `"pro"` \| `"enterprise"`) |
| `detail.used` | integer | Number of variants generated today |
| `detail.limit` | integer | Daily quota for user's plan |

### Frontend Handling
```typescript
try {
  const variant = await generateVariant(recipeId, variantType, options);
} catch (err) {
  if (err instanceof ApiError && err.statusCode === 402) {
    // Show PlanGuard upsell component
    const { plan, used, limit } = err.details.detail;
    // Display: "You've used {used}/{limit} variants on the {plan} plan"
  }
}
```

---

## Daily Quota Limits

### Backend Constants
**File:** `apps/api/tasteos_api/core/quotas.py`

```python
DAILY_VARIANT_QUOTAS = {
    "free": 3,
    "pro": 30,
    "enterprise": 60,
}
```

### Frontend Constants
**File:** `apps/app/src/lib/planLimits.ts`

```typescript
export const PLAN_LIMITS = {
  free: {
    dailyVariantQuota: 3,
    displayName: 'Free',
    price: '$0/month',
  },
  pro: {
    dailyVariantQuota: 30,
    displayName: 'Pro',
    price: '$9.99/month',
  },
  enterprise: {
    dailyVariantQuota: 60,
    displayName: 'Enterprise',
    price: 'Contact us',
  },
}
```

### Plan Comparison
| Plan | Daily Variants | Price | Best For |
|------|----------------|-------|----------|
| Free | 3 | $0/month | Trying out TasteOS |
| Pro | 30 | $9.99/month | Regular home cooks |
| Enterprise | 60 | Contact us | Professional chefs, teams |

---

## Quota Enforcement Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Quota Check Flow                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend:                                              │
│    1. Call getBillingPlan()                             │
│    2. Check canGenerateVariant(plan, used)              │
│    3. If false → Show PlanGuard upsell                  │
│    4. If true → Enable "Generate" button                │
│                                                         │
│  User Action:                                           │
│    5. Click "Generate Variant"                          │
│                                                         │
│  Backend:                                               │
│    6. Receive POST /variants/generate                   │
│    7. Call check_variant_quota(user, session)           │
│    8. If used >= limit → Return 402 with details        │
│    9. If within limit → Generate variant                │
│   10. Call record_variant_usage(...)                    │
│                                                         │
│  Frontend:                                              │
│   11. On success → Display variant                      │
│   12. On 402 → Show PlanGuard with error details        │
│   13. Refresh getBillingPlan() → Update quota display   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Database Schema

### variant_usage Table

```sql
CREATE TABLE variant_usage (
    id INTEGER PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    recipe_id UUID NOT NULL REFERENCES recipes(id),
    variant_type VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX ix_variant_usage_user_id ON variant_usage(user_id);
CREATE INDEX ix_variant_usage_variant_type ON variant_usage(variant_type);
CREATE INDEX ix_variant_usage_created_at ON variant_usage(created_at);
```

### Query for Daily Usage
```python
# Count variants generated today by user
today = date.today()
start_of_day = datetime.combine(today, datetime.min.time())
end_of_day = datetime.combine(today, datetime.max.time())

result = await session.execute(
    select(VariantUsage)
    .where(VariantUsage.user_id == user_id)
    .where(VariantUsage.created_at >= start_of_day)
    .where(VariantUsage.created_at <= end_of_day)
)
usage_count = len(result.scalars().all())
```

---

## Implementation Files

### Backend
- `apps/api/tasteos_api/models/variant_usage.py` - Usage tracking model
- `apps/api/tasteos_api/core/quotas.py` - Quota constants and helpers
- `apps/api/tasteos_api/routers/billing.py` - `/billing/plan` endpoint
- `apps/api/tasteos_api/routers/variants.py` - Quota check in `/generate`

### Frontend
- `apps/app/src/lib/api.ts` - API client with `getBillingPlan()`, `generateVariant()`
- `apps/app/src/lib/planLimits.ts` - Quota constants and helpers
- `apps/app/src/lib/useVariants.ts` - React hook for variant generation
- `apps/app/src/components/VariantPanel.tsx` - Quota display and PlanGuard integration
- `packages/ui/src/components/plan-guard.tsx` - Upsell gate component

---

## Testing Quota System

### 1. Check Current Quota
```bash
curl http://127.0.0.1:8000/api/v1/billing/plan \
  -H "Authorization: Bearer <token>"
```

### 2. Generate Variants Until Quota Hit
```bash
# Generate 1st variant
curl -X POST http://127.0.0.1:8000/api/v1/variants/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": "uuid-here", "variant_type": "dietary"}'

# Repeat 2 more times for free tier...
# 4th request should return 402
```

### 3. Verify 402 Response
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

### 4. Frontend Test Flow
1. Login at `/login`
2. Go to `/recipes/:id`
3. Click "Variants" tab
4. Generate 3 variants (should succeed)
5. Try 4th variant (should show PlanGuard)
6. Click "Billing" (should show 3/3 used)

---

## Version History

- **2025-10-28**: Initial blessed contracts (Phase 1 completion)

---

**Status:** ✅ Production-stable  
**Changes:** Require explicit approval and version bump
