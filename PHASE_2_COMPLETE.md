# Phase 2 Complete: Import, Nutrition, and Stripe Integration

**Date:** January 2025  
**Status:** ✅ Core Features Complete  
**Remaining:** UI polish (nutrition tabs/deltas), test coverage

---

## Overview

Phase 2 adds three major feature areas to TasteOS:

1. **AI Recipe Import** — Import recipes from URLs or images via AI parsing
2. **Nutrition Analysis** — Automatic macro calculation per recipe/variant with caching
3. **Stripe Integration** — Real subscription billing with checkout, portal, and webhooks

---

## 1. AI Recipe Import

### Architecture

```
User Input (URL or Image)
    ↓
POST /imports
    ↓
RecipeImporter Agent (OpenAI GPT-4)
    ↓
[URL Path]                    [Image Path]
    ↓                             ↓
BeautifulSoup Scraper      OCR Placeholder
    ↓                             ↓
schema.org LD+JSON          Raw text → AI
    ↓                             ↓
    ↓────────── Structured Recipe ────────↓
                    ↓
            Save to DB (recipes table)
                    ↓
            Return Recipe ID
```

### Files Created

- **`apps/api/tasteos_api/agents/recipe_importer.py`**  
  Core agent with URL scraping (BeautifulSoup, schema.org) and image OCR placeholder.

- **`apps/api/tasteos_api/routers/imports.py`**  
  Endpoints:
  - `POST /imports` — Accepts `source_url` or `image_file`, returns created recipe
  
- **`apps/app/src/routes/import.tsx`**  
  Frontend route with URL input and file upload UI

- **`apps/api/tasteos_api/tests/test_imports.py`**  
  Tests for URL import (mocked) and error handling

### Dependencies Added

```toml
beautifulsoup4 = ">=4.12.0"
```

### API Contract

**Request:**
```bash
POST /imports
Content-Type: multipart/form-data

# URL import
source_url=https://example.com/recipe

# OR image import
image_file=<file>
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Chocolate Chip Cookies",
  "description": "Classic cookies...",
  "ingredients": [...],
  "instructions": [...],
  "created_at": "2025-01-15T12:00:00Z"
}
```

### Testing

```bash
# Run import tests
pytest apps/api/tasteos_api/tests/test_imports.py -v
```

---

## 2. Nutrition Analysis

### Architecture

```
Recipe/Variant Request
    ↓
GET /recipes/{id}/nutrition
GET /variants/{id}/nutrition
    ↓
Check recipe_nutrition cache
    ↓
[Cache Hit]              [Cache Miss]
    ↓                         ↓
Return cached        NutritionAnalyzer Agent
                              ↓
                    [Stub Mode]  [Edamam/USDA API]
                         ↓               ↓
                    Estimates      Real nutrition data
                         ↓               ↓
                         └───────────────┘
                              ↓
                    Cache in recipe_nutrition
                              ↓
                    Return macros (calories, protein, carbs, fats)
```

### Files Created

- **`apps/api/tasteos_api/agents/nutrition_analyzer.py`**  
  Multi-provider agent (stub/edamam/usda) for ingredient → macros calculation.

- **`apps/api/tasteos_api/models/recipe_nutrition.py`**  
  Caching table:
  ```python
  class RecipeNutrition(BaseModel, table=True):
      recipe_id: UUID
      variant_id: Optional[UUID]
      calories: Optional[int]
      protein: Optional[int]
      carbs: Optional[int]
      fats: Optional[int]
      provider: str  # "stub", "edamam", "usda"
      calculated_at: datetime
  ```

- **`apps/api/tasteos_api/routers/nutrition.py`**  
  Endpoints:
  - `GET /recipes/{recipe_id}/nutrition` — Returns macros for base recipe
  - `GET /variants/{variant_id}/nutrition` — Returns macros for specific variant

- **`packages/ui/src/components/nutrition-panel.tsx`**  
  UI component with macro bar chart and legend:
  ```tsx
  <NutritionPanel
    calories={520}
    protein={24}
    carbs={68}
    fats={18}
  />
  ```

- **`packages/ui/src/components/nutrition-bar.tsx`**  
  Horizontal bar chart (protein=red, carbs=yellow, fats=blue)

- **`packages/ui/src/components/macro-badge.tsx`**  
  Stat badge with label + value + unit

### API Contract

**Request:**
```bash
GET /recipes/{recipe_id}/nutrition
GET /variants/{variant_id}/nutrition
```

**Response:**
```json
{
  "calories": 520,
  "protein_g": 24.0,
  "carbs_g": 45.0,
  "fat_g": 22.0,
  "notes": "Standard nutrition profile"
}
```

### Testing

```bash
# Run nutrition tests
pytest apps/api/tasteos_api/tests/test_nutrition.py -v
```

**Test Coverage:**
- ✅ Recipe nutrition calculation and caching
- ✅ Variant nutrition calculation and caching
- ✅ Cache hit vs cache miss behavior
- ✅ Unauthorized access handling
- ✅ Not found error handling
- ✅ Response format validation

### UI Integration Status

- ✅ **Components Created**: NutritionPanel, NutritionBar, MacroBadge exported from `@tasteos/ui`
- ✅ **RecipeDetail Tab**: "Nutrition" tab added to `recipe-detail.tsx` showing NutritionPanel
- ✅ **VariantPanel Deltas**: Nutrition comparison badges showing deltas (e.g., "-70 kcal", "+8g protein 💪")
- ✅ **API Integration**: Frontend uses `getRecipeNutrition()` and `getVariantNutrition()` from api.ts

**Frontend Implementation:**
- **NutritionPanel Component**: Fetches and displays nutrition data with loading/error states
- **RecipeDetail Route**: Three-tab layout (Base Recipe | Variants | Nutrition)
- **VariantPanel Component**: Automatically loads base and variant nutrition, displays delta badges for:
  - Calories (in kcal)
  - Protein (in g, shows 💪 emoji when increased)
  - Carbs (in g)
  - Fat (in g)
- **Delta Calculation**: Compares each variant's macros to base recipe and shows positive/negative changes

---

## 3. Stripe Integration

### Architecture

```
Frontend: settings-billing.tsx
    ↓
[Subscribe Button]          [Manage Billing Button]
    ↓                              ↓
POST /checkout-session        GET /portal
    ↓                              ↓
Stripe.checkout.sessions.create  Stripe.billingPortal.sessions.create
    ↓                              ↓
Return checkout_url           Return portal_url
    ↓                              ↓
Redirect user                 Redirect user
    ↓                              ↓
User completes payment        User manages subscription
    ↓
Stripe webhook → POST /webhook
    ↓
Log to billing_events table
    ↓
Dispatch to event handler:
    - checkout.session.completed → Update user plan + subscription_status
    - customer.subscription.updated → Update subscription_status
    - customer.subscription.deleted → Set subscription_status = "canceled"
    - invoice.payment_failed → Set subscription_status = "past_due"
    ↓
Mark event as processed
```

### Files Created/Modified

- **`apps/api/tasteos_api/models/billing_event.py`** (CREATED)  
  Audit log for all Stripe webhook events:
  ```python
  class BillingEvent(BaseModel, table=True):
      user_id: Optional[UUID]
      event_type: str  # "checkout.session.completed", etc.
      stripe_event_id: str = Field(unique=True, index=True)
      stripe_customer_id: Optional[str]
      event_data: str = Field(sa_column=Column(JSON))  # Full event payload
      processed: bool = Field(default=False)
      processed_at: Optional[datetime] = None
      error_message: Optional[str] = None  # Logs processing failures
  ```

- **`apps/api/tasteos_api/models/user.py`** (MODIFIED)  
  Added fields:
  ```python
  # In UserBase:
  subscription_status: str = "active"  # active, past_due, canceled, trialing
  
  # In User:
  stripe_customer_id: Optional[str] = None  # Links to Stripe customer
  ```

- **`apps/api/tasteos_api/routers/billing.py`** (EXTENSIVELY MODIFIED)  
  Endpoints:
  - `POST /checkout-session` — Creates Stripe checkout (accepts `interval: "monthly" | "yearly"`)
  - `GET /portal` — Creates Stripe portal session for subscription management
  - `POST /webhook` — Processes Stripe webhook events (logs to `billing_events`, updates user)

- **`apps/app/src/lib/api.ts`** (MODIFIED)  
  Renamed functions:
  ```typescript
  export async function startCheckout(interval: "monthly" | "yearly"): Promise<{checkout_url: string}>
  export async function getBillingPortal(): Promise<{portal_url: string}>
  ```

- **`apps/app/src/routes/settings-billing.tsx`** (MODIFIED)  
  Updated to use `startCheckout("monthly")` and `getBillingPortal()`

### Dependencies Added

```toml
stripe = ">=10.0.0"
```

### Configuration

Add to `.env`:

```bash
# Stripe API keys (from Stripe Dashboard → Developers → API keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe price IDs (from Stripe Dashboard → Products)
STRIPE_PRICE_MONTHLY=price_monthly_123
STRIPE_PRICE_YEARLY=price_yearly_456

# Frontend URLs for redirect (after checkout success/cancel)
FRONTEND_URL=http://localhost:5173
```

### API Contracts

#### Checkout Session

**Request:**
```bash
POST /checkout-session
Content-Type: application/json
Authorization: Bearer <token>

{
  "interval": "monthly"  # or "yearly"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

**Flow:**
1. Validates `interval` is "monthly" or "yearly"
2. Gets `price_id` from `STRIPE_PRICES` config
3. Creates Stripe customer if `user.stripe_customer_id` is None
4. Creates checkout session with:
   - `success_url`: `{FRONTEND_URL}/settings/billing?success=true`
   - `cancel_url`: `{FRONTEND_URL}/settings/billing?canceled=true`
   - Metadata: `user_id`, `plan`
5. Returns `checkout_url` for redirect

#### Customer Portal

**Request:**
```bash
GET /portal
Authorization: Bearer <token>
```

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/p/session/..."
}
```

**Flow:**
1. Gets user's `stripe_customer_id`
2. Creates portal session with `return_url`: `{FRONTEND_URL}/settings/billing`
3. Returns `portal_url` for redirect

#### Webhook

**Request:**
```bash
POST /webhook
Content-Type: application/json
Stripe-Signature: t=...,v1=...

{
  "id": "evt_...",
  "type": "checkout.session.completed",
  "data": { ... }
}
```

**Response:**
```json
{
  "status": "success"
}
```

**Flow:**
1. Verifies Stripe signature using `STRIPE_WEBHOOK_SECRET`
2. Logs event to `billing_events` table:
   ```python
   event_record = BillingEvent(
       user_id=user_id,
       event_type=event["type"],
       stripe_event_id=event["id"],
       stripe_customer_id=customer_id,
       event_data=json.dumps(event),
       processed=False
   )
   ```
3. Dispatches to handler based on `event_type`:
   - `checkout.session.completed` → Updates user plan + subscription_status + stripe_customer_id
   - `customer.subscription.updated` → Updates subscription_status from Stripe subscription object
   - `customer.subscription.deleted` → Sets subscription_status = "canceled"
   - `invoice.payment_failed` → Sets subscription_status = "past_due"
4. Marks event as `processed=True` or logs `error_message` on failure

### Testing

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login
stripe login

# Forward webhooks to local API
stripe listen --forward-to http://localhost:8000/billing/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_failed

# Check billing_events table for logged events
```

### Subscription Lifecycle

| Event                           | Action                                                                 |
|---------------------------------|------------------------------------------------------------------------|
| `checkout.session.completed`    | Update `user.plan`, `subscription_status="active"`, `stripe_customer_id` |
| `customer.subscription.updated` | Update `subscription_status` (active, past_due, trialing)             |
| `customer.subscription.deleted` | Set `subscription_status="canceled"`                                   |
| `invoice.payment_failed`        | Set `subscription_status="past_due"`                                   |

### Audit Trail

All webhook events are logged to `billing_events` table with:
- Full event payload (`event_data`)
- Processing status (`processed`, `processed_at`)
- Error messages (`error_message`) for failed processing
- Unique constraint on `stripe_event_id` prevents duplicate processing

---

## Summary

### Completed Features

✅ **Import Flow**
- URL scraping with schema.org parsing
- Image upload with OCR placeholder
- Frontend route with file upload UI
- Tests with mocked scraper

✅ **Nutrition Flow**
- Multi-provider analyzer (stub/edamam/usda)
- Caching in `recipe_nutrition` table
- API endpoints for recipes and variants
- UI components (NutritionPanel, NutritionBar, MacroBadge)
- **Nutrition tab in RecipeDetail** showing full macros breakdown
- **Nutrition delta badges in VariantPanel** comparing each variant to base recipe
- Comprehensive test suite with mocked analyzer

✅ **Stripe Integration**
- Real checkout session creation (monthly/yearly)
- Customer portal access
- Webhook event logging and processing
- Subscription lifecycle management
- Frontend API and UI updates
- **Plan-based quota enforcement** mapped to subscription_status
- **Billing event audit trail** for compliance and debugging

### What's New in This Polish Pass

🎨 **Nutrition UI Implementation:**
- Added "Nutrition" tab to recipe detail page
- NutritionPanel component displays:
  - Total calories per serving
  - Macro breakdown with visual bar chart
  - Individual macro badges (protein, carbs, fat)
  - Notes about nutrition profile
- VariantPanel now shows nutrition comparison:
  - Fetches nutrition for base recipe and all variants
  - Displays delta badges (e.g., "-70 kcal", "+8g protein 💪")
  - Color-coded by macro type
  - Only shows non-zero deltas

🧪 **Testing:**
- Created `test_nutrition.py` with 10 test cases
- Tests cached vs non-cached nutrition
- Tests authorization and error handling
- Mocked analyzer prevents external API calls

📝 **Documentation:**
- Updated PHASE_2_COMPLETE.md with implementation details
- Documented API contracts with correct response format
- Added frontend integration details

### Configuration Checklist

- [ ] Set `STRIPE_SECRET_KEY` in `.env`
- [ ] Set `STRIPE_WEBHOOK_SECRET` in `.env`
- [ ] Set `STRIPE_PRICE_MONTHLY` and `STRIPE_PRICE_YEARLY` in `.env`
- [ ] Configure Stripe webhook endpoint in Stripe Dashboard:
  - URL: `https://your-domain.com/billing/webhook`
  - Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`
- [ ] (Optional) Set `EDAMAM_APP_ID` and `EDAMAM_APP_KEY` for real nutrition data
- [ ] (Optional) Set `USDA_API_KEY` for USDA nutrition database

### Deployment Notes

1. **Database Migration**: Run `alembic upgrade head` to create `billing_events` and `recipe_nutrition` tables and add `subscription_status`/`stripe_customer_id` to `users` table.

2. **Stripe Webhook**: Configure webhook URL in Stripe Dashboard → Webhooks → Add endpoint:
   ```
   https://api.tasteos.com/billing/webhook
   ```
   Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`

3. **Environment Variables**: Ensure all Stripe keys and price IDs are set in production `.env`

4. **Testing**: Use Stripe CLI to test webhook processing locally before deploying

5. **Stripe Integration Status**: ✅ Stripe is now wired to real checkout/portal endpoints and updates user plan + subscription_status via webhook handlers. Quota gates properly map to plan field and enforce limits.

---

## Next Steps (Phase 3?)

- **Recipe Sharing**: Public recipe links with social preview
- **Meal Planning**: Weekly meal plan generator with shopping lists
- **Grocery Integration**: One-click delivery via Instacart/Amazon Fresh
- **Community Features**: Recipe ratings, comments, forks
- **Advanced AI**: Dietary restrictions, allergen detection, recipe scaling

---

**Phase 2 Status:** ✅ **COMPLETE** — All features implemented, tested, and documented
