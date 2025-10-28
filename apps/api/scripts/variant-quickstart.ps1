#!/usr/bin/env pwsh
# Quick start guide for variant generation

Write-Host @"

╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         🍳 TasteOS Variant Generation - Quick Start 🍳          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Write-Host "📋 Prerequisites:" -ForegroundColor Yellow
Write-Host "   1. API server running (pnpm dev:api)"
Write-Host "   2. OpenAI API key set in .env"
Write-Host "   3. User account with JWT token"
Write-Host ""

Write-Host "🔑 Step 1: Get your token" -ForegroundColor Yellow
Write-Host "   .\apps\api\scripts\login.ps1" -ForegroundColor Gray
Write-Host "   # Token stored in `$env:TASTEOS_TOKEN" -ForegroundColor Green
Write-Host ""

Write-Host "🧪 Step 2: Create a recipe (if you don't have one)" -ForegroundColor Yellow
Write-Host "   .\apps\api\scripts\test_api.ps1 -Token `$env:TASTEOS_TOKEN" -ForegroundColor Gray
Write-Host "   # Creates a Spaghetti Carbonara recipe" -ForegroundColor Green
Write-Host ""

Write-Host "✨ Step 3: Generate variants!" -ForegroundColor Yellow
Write-Host "   .\apps\api\scripts\test_variant.ps1 -Token `$env:TASTEOS_TOKEN" -ForegroundColor Gray
Write-Host ""

Write-Host "🎯 Variant Types:" -ForegroundColor Yellow
Write-Host "   • dietary       - Convert to vegetarian, vegan, gluten-free, etc."
Write-Host "   • cuisine       - Adapt to Italian, Mexican, Asian, etc."
Write-Host "   • ingredient_substitution - Replace specific ingredients"
Write-Host "   • simplify      - Reduce complexity and prep time"
Write-Host "   • upscale       - Elevate with premium ingredients"
Write-Host ""

Write-Host "📊 API Endpoints:" -ForegroundColor Yellow
Write-Host "   POST   /api/v1/variants/generate           - Generate new variant"
Write-Host "   GET    /api/v1/variants/{id}               - Get variant details"
Write-Host "   GET    /api/v1/variants/recipe/{recipe_id} - List all variants"
Write-Host "   POST   /api/v1/variants/{id}/approve       - Approve variant"
Write-Host "   GET    /api/v1/variants/{id}/diff          - Show changes"
Write-Host ""

Write-Host "🔬 Example API Call:" -ForegroundColor Yellow
Write-Host @'
   $body = @{
       recipe_id = "1b2e92aa-..."
       variant_type = "dietary"
       dietary_restriction = "vegetarian"
   } | ConvertTo-Json

   Invoke-RestMethod `
       -Uri "http://localhost:8000/api/v1/variants/generate" `
       -Method POST `
       -Headers @{ "Authorization" = "Bearer $env:TASTEOS_TOKEN" } `
       -Body $body
'@ -ForegroundColor Gray

Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "   • Higher confidence scores (>0.8) mean better variants"
Write-Host "   • Check the 'changes' array for detailed modifications"
Write-Host "   • Use /diff endpoint to see before/after comparison"
Write-Host "   • Approve good variants for future reference"
Write-Host ""

Write-Host "📝 Need help? Check:" -ForegroundColor Yellow
Write-Host "   • VARIANT_GENERATION_COMPLETE.md - Full documentation"
Write-Host "   • /docs endpoint - API documentation"
Write-Host "   • COPILOT_README.md - Development workflow"
Write-Host ""

Write-Host "Ready to generate some amazing recipe variants! 🚀" -ForegroundColor Cyan
Write-Host ""
