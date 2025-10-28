#!/usr/bin/env pwsh
# Test billing and usage tracking endpoints

param(
    [string]$Token = "",
    [string]$ApiBase = "http://127.0.0.1:8000"
)

if ($Token -eq "") {
    Write-Host "ERROR: Token is required. Usage: .\test_billing.ps1 -Token <your_token>" -ForegroundColor Red
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TasteOS Billing & Usage Tests" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Get subscription status
Write-Host "=== TEST 1: Get Subscription ===" -ForegroundColor Yellow
try {
    $subscription = Invoke-RestMethod -Uri "$ApiBase/api/v1/billing/subscription" -Headers $headers

    Write-Host "✓ SUCCESS" -ForegroundColor Green
    Write-Host "  Plan: $($subscription.plan)" -ForegroundColor Cyan
    Write-Host "  Status: $($subscription.status)" -ForegroundColor Cyan
    Write-Host "  Period End: $($subscription.current_period_end)" -ForegroundColor Cyan

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== TEST 2: Get Usage Stats ===" -ForegroundColor Yellow
try {
    $usage = Invoke-RestMethod -Uri "$ApiBase/api/v1/billing/usage" -Headers $headers

    Write-Host "✓ SUCCESS" -ForegroundColor Green
    Write-Host "  Period: $($usage.period)" -ForegroundColor Cyan
    Write-Host "  Variants Generated: $($usage.variants_generated)" -ForegroundColor Cyan
    Write-Host "  Recipes Imported: $($usage.recipes_imported)" -ForegroundColor Cyan
    Write-Host "  Cooking Sessions: $($usage.cooking_sessions)" -ForegroundColor Cyan

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== TEST 3: Get Plan Limits ===" -ForegroundColor Yellow
try {
    $limits = Invoke-RestMethod -Uri "$ApiBase/api/v1/billing/limits" -Headers $headers

    Write-Host "✓ SUCCESS" -ForegroundColor Green
    Write-Host "`n  Current Plan: $($limits.plan)" -ForegroundColor Cyan

    Write-Host "`n  Limits:" -ForegroundColor Yellow
    Write-Host "    Variants/month: $($limits.limits.variants_per_month)" -ForegroundColor Cyan
    Write-Host "    Recipes/month: $($limits.limits.recipes_imported_per_month)" -ForegroundColor Cyan
    Write-Host "    Sessions/month: $($limits.limits.cooking_sessions_per_month)" -ForegroundColor Cyan

    Write-Host "`n  Current Usage:" -ForegroundColor Yellow
    Write-Host "    Variants: $($limits.usage.variants_generated)" -ForegroundColor Cyan
    Write-Host "    Recipes: $($limits.usage.recipes_imported)" -ForegroundColor Cyan
    Write-Host "    Sessions: $($limits.usage.cooking_sessions)" -ForegroundColor Cyan

    Write-Host "`n  Remaining:" -ForegroundColor Yellow
    if ($limits.remaining.variants -eq -1) {
        Write-Host "    Variants: Unlimited" -ForegroundColor Green
    } else {
        $variantsColor = if ($limits.remaining.variants -lt 3) { "Red" } elseif ($limits.remaining.variants -lt 5) { "Yellow" } else { "Green" }
        Write-Host "    Variants: $($limits.remaining.variants)" -ForegroundColor $variantsColor
    }
    Write-Host "    Recipes: $($limits.remaining.recipes)" -ForegroundColor Cyan
    Write-Host "    Sessions: $($limits.remaining.sessions)" -ForegroundColor Cyan

    # Show upgrade prompt if running low
    if ($limits.remaining.variants -ne -1 -and $limits.remaining.variants -lt 3) {
        Write-Host "`n  ⚠️  WARNING: Low on variants! Consider upgrading." -ForegroundColor Yellow
    }

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== TEST 4: Test Usage Limit Enforcement ===" -ForegroundColor Yellow
try {
    # Get current limits
    $limits = Invoke-RestMethod -Uri "$ApiBase/api/v1/billing/limits" -Headers $headers

    if ($limits.remaining.variants -eq 0) {
        Write-Host "✓ At limit - testing enforcement" -ForegroundColor Yellow

        # Try to generate a variant (should fail)
        $recipes = Invoke-RestMethod -Uri "$ApiBase/api/v1/recipes/" -Headers $headers
        if ($recipes.Count -gt 0) {
            $recipeId = $recipes[0].id

            $body = @{
                recipe_id = $recipeId
                variant_type = "dietary"
                dietary_restriction = "vegetarian"
            } | ConvertTo-Json

            try {
                Invoke-RestMethod `
                    -Uri "$ApiBase/api/v1/variants/generate" `
                    -Method POST `
                    -Headers $headers `
                    -Body $body

                Write-Host "✗ FAILED: Limit not enforced!" -ForegroundColor Red
            } catch {
                if ($_.Exception.Response.StatusCode -eq 429) {
                    Write-Host "✓ SUCCESS: Limit properly enforced (429 error)" -ForegroundColor Green

                    # Parse error message
                    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                    $errorBody = $reader.ReadToEnd() | ConvertFrom-Json
                    Write-Host "  Message: $($errorBody.detail)" -ForegroundColor Cyan
                } else {
                    Write-Host "✗ FAILED: Wrong error code" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "✓ Not at limit yet ($($limits.remaining.variants) remaining)" -ForegroundColor Green
        Write-Host "  Generate more variants to test limit enforcement" -ForegroundColor Cyan
    }

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== TEST 5: Create Checkout Session (Test Only) ===" -ForegroundColor Yellow
try {
    $body = @{
        price_id = "price_pro_monthly"
        success_url = "http://localhost:3000/success"
        cancel_url = "http://localhost:3000/cancel"
    } | ConvertTo-Json

    $checkout = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/billing/create-checkout-session" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host "✓ SUCCESS - Checkout session created" -ForegroundColor Green
    Write-Host "  Checkout URL: $($checkout.checkout_url)" -ForegroundColor Cyan
    Write-Host "  Session ID: $($checkout.session_id)" -ForegroundColor Cyan
    Write-Host "`n  Note: URL won't work without Stripe config" -ForegroundColor Yellow

} catch {
    if ($_.Exception.Message -like "*Stripe*") {
        Write-Host "⚠️  EXPECTED: Stripe not configured" -ForegroundColor Yellow
        Write-Host "  Add STRIPE_SECRET_KEY to .env to enable" -ForegroundColor Cyan
    } else {
        Write-Host "✗ FAILED" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Billing tests complete" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Configure Stripe keys in .env" -ForegroundColor Cyan
Write-Host "  2. Set up products in Stripe Dashboard" -ForegroundColor Cyan
Write-Host "  3. Test full checkout flow" -ForegroundColor Cyan
Write-Host "  4. Configure webhooks for production" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
