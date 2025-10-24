# SQLite Local Database Setup
# Quick start script to set up local database with live price data

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('full', 'quick')]
    [string]$Mode = 'quick'
)

Write-Host "🗄️  Setting up local SQLite database..." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Green
& .venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "Step 1: Creating database schema..." -ForegroundColor Yellow
python database/init_sqlite.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create database" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Fetching live price data from Binance..." -ForegroundColor Yellow

if ($Mode -eq 'quick') {
    Write-Host "   (Quick mode - last 24 hours only)" -ForegroundColor Gray
    python database/fetch_live_data.py quick
} else {
    Write-Host "   (Full mode - 7 days hourly + 200 days daily)" -ForegroundColor Gray
    python database/fetch_live_data.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to fetch data" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Verifying database..." -ForegroundColor Yellow
python database/init_sqlite.py verify

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "✅ Local database ready!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "Database file: local_crypto.db" -ForegroundColor Cyan
Write-Host "Contains: REAL price data from Binance" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Make sure DATABASE_TYPE=sqlite in your .env file" -ForegroundColor White
Write-Host "  2. Run your reports: .\run-local.ps1 daily" -ForegroundColor White
Write-Host ""
Write-Host "To refresh data later:" -ForegroundColor Yellow
Write-Host "  python database/fetch_live_data.py quick" -ForegroundColor White
