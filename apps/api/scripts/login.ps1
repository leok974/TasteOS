param(
    [string]$Email = "test@example.com",
    [string]$Password = "testpassword123",
    [string]$ApiBase = "http://127.0.0.1:8000"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TasteOS API Login Helper" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "$ApiBase/api/v1/auth/login" `
        -Method POST `
        -Body "username=$Email&password=$Password" `
        -ContentType "application/x-www-form-urlencoded"

    $token = $response.access_token

    # Store token in environment variable
    $env:TASTEOS_TOKEN = $token

    # Save token to gitignored scratch file for persistence
    $scratchDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) ".mcp\scratch"
    New-Item -ItemType Directory -Force -Path $scratchDir | Out-Null
    $tokenFile = Join-Path $scratchDir "token.local.txt"
    $token | Out-File -FilePath $tokenFile -Encoding UTF8 -NoNewline

    Write-Host "✓ Login successful!" -ForegroundColor Green
    Write-Host "`nUser Info:" -ForegroundColor Yellow
    Write-Host "  Email: $($response.user.email)"
    Write-Host "  Name: $($response.user.name)"
    Write-Host "  Plan: $($response.user.plan)"
    Write-Host "  ID: $($response.user.id)"

    Write-Host "`nAccess Token:" -ForegroundColor Yellow
    Write-Host "  TASTEOS_TOKEN=***REDACTED*** (length: $($token.Length))" -ForegroundColor Gray
    Write-Host "  Stored in: `$env:TASTEOS_TOKEN" -ForegroundColor Gray
    Write-Host "  Persisted to: $tokenFile" -ForegroundColor Gray

    Write-Host "`nTo use in tests, run:" -ForegroundColor Yellow
    Write-Host "  .\scripts\test_api.ps1 -Token `$env:TASTEOS_TOKEN" -ForegroundColor Gray

    Write-Host "`n========================================`n" -ForegroundColor Cyan

} catch {
    Write-Host "✗ Login failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
