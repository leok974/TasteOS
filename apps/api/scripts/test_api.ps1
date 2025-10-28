param(
    [string]$Token = "",
    [string]$ApiBase = "http://127.0.0.1:8000",
    [switch]$SaveLog
)

if ($Token -eq "") {
    Write-Host "ERROR: Token is required. Usage: .\test_api.ps1 -Token <your_token>" -ForegroundColor Red
    exit 1
}

# Setup logging if requested
$logContent = @()
$timestamp = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
$logPath = ""

if ($SaveLog) {
    $logsDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "LOGS"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    $logPath = Join-Path $logsDir "smoke_$timestamp.txt"
}

function Log-Message {
    param([string]$Message)
    Write-Host $Message
    if ($SaveLog) {
        $script:logContent += $Message
    }
}

# Ensure LOGS directory exists
New-Item -ItemType Directory -Force -Path (Join-Path (Resolve-Path ..\\..) "LOGS") | Out-Null

$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

Log-Message ""
Log-Message "========================================"
Log-Message "TasteOS API Smoke Test"
Log-Message "API Base: $ApiBase"
Log-Message "Token: ***REDACTED*** (length $($Token.Length))"
Log-Message "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Log-Message "========================================"
Log-Message ""

# 1. Test /auth/me
Log-Message "=== TEST 1: GET /auth/me ==="
try {
    $me = Invoke-RestMethod -Uri "$ApiBase/api/v1/auth/me" -Headers $headers
    Log-Message "✓ SUCCESS"
    Log-Message ($me | ConvertTo-Json -Depth 10)
} catch {
    Log-Message "✗ FAILED"
    Log-Message $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Log-Message "Response: $responseBody"
    }
}

Log-Message ""

# 2. Test GET /recipes
Log-Message "=== TEST 2: GET /recipes ==="
try {
    $recipes = Invoke-RestMethod -Uri "$ApiBase/api/v1/recipes/" -Headers $headers
    Log-Message "✓ SUCCESS - Found $($recipes.Count) recipes"
    Log-Message ($recipes | ConvertTo-Json -Depth 10)
} catch {
    Log-Message "✗ FAILED"
    Log-Message $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Log-Message "Response: $responseBody"
    }
}

Log-Message ""

# 3. Test POST /recipes (create sample recipe)
Log-Message "=== TEST 3: POST /recipes ==="
$body = @{
    title = "Spaghetti Carbonara"
    description = "Classic Italian pasta dish"
    servings = 4
    prep_time = 10
    cook_time = 20
    difficulty = "medium"
    cuisine = "italian"
    tags = @("pasta", "italian", "dinner")
    ingredients = @(
        @{ item = "spaghetti"; amount = "400g"; notes = "" }
        @{ item = "eggs"; amount = "4"; notes = "" }
        @{ item = "parmesan"; amount = "100g"; notes = "grated" }
    )
    instructions = @(
        @{ step = 1; text = "Boil pasta in salted water" }
        @{ step = 2; text = "Mix eggs and cheese in a bowl" }
        @{ step = 3; text = "Drain pasta and mix with egg mixture" }
    )
} | ConvertTo-Json -Depth 10

try {
    $create = Invoke-RestMethod -Uri "$ApiBase/api/v1/recipes/" -Method POST -Headers $headers -Body $body
    Log-Message "✓ SUCCESS - Created recipe with ID: $($create.id)"
    Log-Message ($create | ConvertTo-Json -Depth 10)
} catch {
    Log-Message "✗ FAILED"
    Log-Message $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Log-Message "Response: $responseBody"
    }
}

Log-Message ""
Log-Message "========================================"
Log-Message "Smoke test complete"
Log-Message "========================================"
Log-Message ""

# Save log file and output path for MCP/Copilot
if ($SaveLog) {
    $logContent | Out-File -FilePath $logPath -Encoding UTF8
    Write-Host "✓ Log saved to: $logPath" -ForegroundColor Green
}
