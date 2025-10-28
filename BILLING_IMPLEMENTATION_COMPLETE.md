# ✅ Stripe Billing Implementation Complete

## Summary

Implemented full Stripe billing integration with subscription management, usage tracking, and webhook handling for TasteOS.

## What Was Implemented

### 1. Database Models

**Subscription Model** (`tasteos_api/models/subscription.py`)
```python
- plan: free, pro, enterprise
- status: active, canceled, past_due, unpaid, trialing  
- stripe_subscription_id, stripe_customer_id
- period start/end tracking
```

**Usage Model** (`tasteos_api/models/usage.py`)
```python
- Tracks monthly usage by period (YYYY-MM)
- variants_generated, recipes_imported, cooking_sessions
- Linked to user for quota enforcement
```

### 2. Plan Limits

```python
FREE TIER:
- 10 variants/month
- 5 recipes imported/month
- 50 cooking sessions/month

PRO TIER ($9.99/mo):
- 100 variants/month
- 50 recipes imported/month
- 500 cooking sessions/month

ENTERPRISE:
- Unlimited everything
```

### 3. API Endpoints

✅ **GET /api/v1/billing/subscription** - Get current subscription
✅ **POST /api/v1/billing/create-checkout-session** - Start Stripe checkout
✅ **POST /api/v1/billing/webhook** - Handle Stripe webhooks
✅ **POST /api/v1/billing/cancel-subscription** - Cancel subscription
✅ **GET /api/v1/billing/usage** - Get current usage stats
✅ **GET /api/v1/billing/limits** - Get plan limits and remaining quota

### 4. Webhook Handlers

- ✅ `checkout.session.completed` - Activate subscription after payment
- ✅ `customer.subscription.updated` - Update subscription status
- ✅ `customer.subscription.deleted` - Handle cancellation
- ✅ `invoice.payment_failed` - Mark subscription as past_due

### 5. Usage Tracking

**Helper Functions:**
```python
check_usage_limit(user, feature, session)  # Returns True if within limits
increment_usage(user, feature, session)     # Increment usage counter
```

**Integration:**
- Variant generation checks limits before allowing generation
- Auto-increments usage counter after successful variant creation
- Returns 429 error if limit exceeded

## Usage Flow

### 1. User Signs Up
```
→ Auto-created with FREE plan
→ No Stripe customer yet
→ Usage tracking starts
```

### 2. User Generates Variants
```
→ Check usage limit
→ If exceeded: 429 error with upgrade message
→ If within limit: Generate variant
→ Increment usage counter
```

### 3. User Upgrades to Pro
```
→ Frontend calls /billing/create-checkout-session
→ User redirected to Stripe Checkout
→ After payment: webhook creates subscription
→ User gets Pro limits immediately
```

### 4. Subscription Management
```
→ View current plan: GET /billing/subscription
→ Cancel plan: POST /billing/cancel-subscription
→ Check usage: GET /billing/limits
```

## Testing

### Prerequisites

1. **Stripe Account** - Get test API keys from https://dashboard.stripe.com/test/apikeys
2. **Stripe CLI** (optional) - For testing webhooks locally

### Environment Variables

Update `.env`:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...  # From Stripe CLI or dashboard
```

### Test Checkout Flow

```python
# 1. Get user token
.\apps\api\scripts\login.ps1

# 2. Create checkout session
$body = @{
    price_id = "price_pro_monthly"
    success_url = "http://localhost:3000/success"
    cancel_url = "http://localhost:3000/cancel"
} | ConvertTo-Json

$checkout = Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/billing/create-checkout-session" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $env:TASTEOS_TOKEN" } `
    -Body $body

# Open checkout URL
Start-Process $checkout.checkout_url
```

### Test Webhooks Locally

```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8000/api/v1/billing/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger invoice.payment_failed
```

### Test Usage Tracking

```powershell
# 1. Check current usage
$usage = Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/billing/limits" `
    -Headers @{ "Authorization" = "Bearer $env:TASTEOS_TOKEN" }

Write-Host "Plan: $($usage.plan)"
Write-Host "Variants used: $($usage.usage.variants_generated) / $($usage.limits.variants_per_month)"
Write-Host "Variants remaining: $($usage.remaining.variants)"

# 2. Generate variants until limit hit
for ($i = 0; $i -lt 15; $i++) {
    try {
        # This will succeed for first 10, then fail with 429
        .\apps\api\scripts\test_variant.ps1 -Token $env:TASTEOS_TOKEN
    } catch {
        Write-Host "Limit reached!" -ForegroundColor Red
        break
    }
}
```

## Stripe Dashboard Setup

### 1. Create Products

In Stripe Dashboard > Products, create:

**Pro Monthly**
- Name: "TasteOS Pro - Monthly"
- Price: $9.99/month recurring
- Copy Price ID → Update .env

**Pro Yearly**  
- Name: "TasteOS Pro - Yearly"
- Price: $99/year recurring (2 months free)
- Copy Price ID → Update .env

### 2. Configure Webhooks

In Stripe Dashboard > Developers > Webhooks, add endpoint:

**URL:** `https://yourdomain.com/api/v1/billing/webhook`

**Events to listen for:**
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`

**Copy webhook signing secret** → Update .env as `STRIPE_WEBHOOK_SECRET`

## Security

✅ **Webhook Verification** - Validates Stripe signature on all webhooks
✅ **Customer Matching** - Links Stripe customers to users via metadata
✅ **Plan Enforcement** - Checks limits before every variant generation
✅ **Cancel Protection** - Cancels at period end (user keeps access until paid period ends)
✅ **Error Handling** - Graceful degradation on Stripe API errors

## Frontend Integration

### Checkout Flow

```typescript
// 1. Create checkout session
const response = await fetch('/api/v1/billing/create-checkout-session', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    price_id: 'price_pro_monthly',
    success_url: `${window.location.origin}/success`,
    cancel_url: `${window.location.origin}/cancel`
  })
});

const { checkout_url } = await response.json();

// 2. Redirect to Stripe
window.location.href = checkout_url;
```

### Usage Display

```typescript
// Get usage and limits
const limits = await fetch('/api/v1/billing/limits', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// Show progress bar
const percentage = (limits.usage.variants_generated / limits.limits.variants_per_month) * 100;

console.log(`${limits.usage.variants_generated} / ${limits.limits.variants_per_month} variants used`);
console.log(`${limits.remaining.variants} remaining this month`);
```

### Upgrade Prompt

```typescript
// Show upgrade prompt when limit hit
if (error.status === 429) {
  showUpgradeModal({
    title: "Variant Generation Limit Reached",
    message: "You've used all 10 free variants this month.",
    cta: "Upgrade to Pro for 100 variants/month",
    action: () => redirectToCheckout('price_pro_monthly')
  });
}
```

## Cost Analysis

### Revenue Model

**Pro Plan: $9.99/month**
- Cost per variant: ~$0.08 (GPT-4 tokens)
- User gets: 100 variants/month
- Cost if fully used: $8.00
- Profit margin: ~20%

**Key Metrics:**
- Need 80%+ users to NOT max out their quota
- Average usage: ~30 variants/month = $2.40 cost
- Healthy margins at scale

### Optimization Strategies

1. **Prompt Optimization** - Reduce token usage per variant
2. **Caching** - Cache similar variant requests
3. **Model Selection** - Use GPT-3.5 for simple variants
4. **Batch Processing** - Generate multiple variants in one LLM call

## Next Steps

### Immediate

1. **Add Stripe test keys** to `.env`
2. **Create products** in Stripe Dashboard
3. **Test checkout flow** end-to-end
4. **Test webhooks** with Stripe CLI

### Frontend Tasks

1. **Pricing page** - Show plans with features
2. **Checkout integration** - Embed Stripe Checkout
3. **Account page** - Show current plan and usage
4. **Usage indicators** - Progress bars on variant generation
5. **Upgrade prompts** - Show when limits approached

### Future Enhancements

1. **Annual billing** - Offer yearly discount
2. **Team plans** - Multiple users, shared quota
3. **Add-ons** - Buy extra variants à la carte
4. **Usage alerts** - Email when 80% quota used
5. **Invoice history** - Show past payments
6. **Payment methods** - Update card details

## Troubleshooting

### "No active subscription found"
- User needs to complete checkout first
- Check Stripe Dashboard for failed payments

### "Webhook signature verification failed"  
- Verify `STRIPE_WEBHOOK_SECRET` in .env
- Check webhook endpoint in Stripe Dashboard

### "Usage not incrementing"
- Check database has `usage` table
- Verify `increment_usage()` called after variant generation

### "429 error even with Pro plan"
- Check subscription status in database
- Verify webhook successfully updated subscription
- Check current period hasn't expired

## Documentation

- **Stripe API Docs**: https://stripe.com/docs/api
- **Webhook Events**: https://stripe.com/docs/api/events/types
- **Testing**: https://stripe.com/docs/testing

---

**Implementation Status:** ✅ Complete
**Testing Status:** 🧪 Ready for testing
**Production Ready:** ⚠️ Needs Stripe configuration
