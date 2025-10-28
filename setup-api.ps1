# TasteOS Python API Setup Script

Write-Host "🍳 TasteOS API Setup" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11 or higher from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check Python version
$pythonVersion = python --version
Write-Host "✅ Found $pythonVersion" -ForegroundColor Green

# Navigate to API directory
Set-Location -Path "$PSScriptRoot\apps\api"

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host ""
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host ""
Write-Host "📦 Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy .env.example to .env and configure your environment variables"
Write-Host "2. Run 'pnpm dev:api' from the root directory to start the API server"
Write-Host ""
Write-Host "To activate the virtual environment manually, run:" -ForegroundColor Yellow
Write-Host "  .\apps\api\venv\Scripts\Activate.ps1"
Write-Host ""
