#!/usr/bin/env pwsh
# Test variant generation endpoint

param(
    [string]$Token = "",
    [string]$ApiBase = "http://127.0.0.1:8000"
)

if ($Token -eq "") {
    Write-Host "ERROR: Token is required. Usage: .\test_variant.ps1 -Token <your_token>" -ForegroundColor Red
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TasteOS Variant Generation Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Get existing recipes
Write-Host "=== Getting Recipes ===" -ForegroundColor Yellow
try {
    $recipes = Invoke-RestMethod -Uri "$ApiBase/api/v1/recipes/" -Headers $headers

    if ($recipes.Count -eq 0) {
        Write-Host "No recipes found. Please create a recipe first." -ForegroundColor Red
        exit 1
    }

    $recipe = $recipes[0]
    $recipeId = $recipe.id
    Write-Host "✓ Found recipe: $($recipe.title) (ID: $recipeId)" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to get recipes" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "`n=== TEST 1: Generate Dietary Variant (Vegetarian) ===" -ForegroundColor Yellow
try {
    $body = @{
        recipe_id = $recipeId
        variant_type = "dietary"
        dietary_restriction = "vegetarian"
    } | ConvertTo-Json

    $variant = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/variants/generate" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host "✓ SUCCESS - Generated variant:" -ForegroundColor Green
    Write-Host "  Title: $($variant.title)" -ForegroundColor Cyan
    Write-Host "  Type: $($variant.variant_type)" -ForegroundColor Cyan
    Write-Host "  Status: $($variant.status)" -ForegroundColor Cyan
    Write-Host "  Confidence: $($variant.confidence_score)" -ForegroundColor Cyan
    Write-Host "  Changes: $($variant.changes.Count) modifications" -ForegroundColor Cyan

    $variantId = $variant.id

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== TEST 2: Generate Cuisine Variant (Italian -> Mexican) ===" -ForegroundColor Yellow
try {
    $body = @{
        recipe_id = $recipeId
        variant_type = "cuisine"
        target_cuisine = "mexican"
    } | ConvertTo-Json

    $variant2 = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/variants/generate" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host "✓ SUCCESS - Generated variant:" -ForegroundColor Green
    Write-Host "  Title: $($variant2.title)" -ForegroundColor Cyan
    Write-Host "  Confidence: $($variant2.confidence_score)" -ForegroundColor Cyan

} catch {
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

if ($variantId) {
    Write-Host "`n=== TEST 3: Get Variant Diff ===" -ForegroundColor Yellow
    try {
        $diff = Invoke-RestMethod -Uri "$ApiBase/api/v1/variants/$variantId/diff" -Headers $headers

        Write-Host "✓ SUCCESS - Retrieved diff:" -ForegroundColor Green
        Write-Host "  Original: $($diff.original.title)" -ForegroundColor Cyan
        Write-Host "  Modified: $($diff.modified.title)" -ForegroundColor Cyan
        Write-Host "  Changes: $($diff.changes.Count)" -ForegroundColor Cyan

    } catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }

    Write-Host "`n=== TEST 4: List All Variants for Recipe ===" -ForegroundColor Yellow
    try {
        $allVariants = Invoke-RestMethod -Uri "$ApiBase/api/v1/variants/recipe/$recipeId" -Headers $headers

        Write-Host "✓ SUCCESS - Found $($allVariants.Count) variants" -ForegroundColor Green
        foreach ($v in $allVariants) {
            Write-Host "  - $($v.title) ($($v.variant_type))" -ForegroundColor Cyan
        }

    } catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }

    Write-Host "`n=== TEST 5: Approve Variant ===" -ForegroundColor Yellow
    try {
        $approved = Invoke-RestMethod `
            -Uri "$ApiBase/api/v1/variants/$variantId/approve" `
            -Method POST `
            -Headers $headers

        Write-Host "✓ SUCCESS - Variant approved" -ForegroundColor Green
        Write-Host "  Status: $($approved.status)" -ForegroundColor Cyan

    } catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Variant generation tests complete" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
