# PowerShell script to run Azure Function locally
# Usage: 
#   .\run-local.ps1                 # Daily report (online if DB available)
#   .\run-local.ps1 offline         # Offline report with mock data
#   .\run-local.ps1 current BTC     # Current situation report
#   .\run-local.ps1 offline BTC     # Offline situation report for BTC

param(
    [Parameter(Mandatory = $false)]
    [string]$ReportType = 'daily',
    
    [Parameter(Mandatory = $false)]
    [string]$Symbol = ''
)

Write-Host "🔧 Running Azure Function Locally" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Yellow
    Write-Host "Please create a .env file based on .env.example" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can copy .env.example to .env and fill in your values:" -ForegroundColor Yellow
    Write-Host "  Copy-Item .env.example .env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "For offline mode (no database needed), just set OFFLINE_MODE=true" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activating virtual environment..." -ForegroundColor Green
    & .venv\Scripts\Activate.ps1
}
else {
    Write-Host "⚠️  Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    & .venv\Scripts\Activate.ps1
    Write-Host "📥 Installing dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
}

Write-Host ""

# Check if offline mode
if ($ReportType -eq 'offline') {
    Write-Host "� OFFLINE MODE - No database required!" -ForegroundColor Magenta
    Write-Host "Using mock data + real news for AI analysis" -ForegroundColor Magenta
}
else {
    Write-Host "🔗 ONLINE MODE - Requires database connection" -ForegroundColor Green
}

Write-Host ""
Write-Host "�🚀 Running $ReportType report..." -ForegroundColor Green
Write-Host ""

# Run the local runner
if ($ReportType -eq 'current' -or ($ReportType -eq 'offline' -and $Symbol)) {
    if ([string]::IsNullOrEmpty($Symbol)) {
        Write-Host "❌ Error: Symbol required" -ForegroundColor Red
        Write-Host "Usage: .\run-local.ps1 current BTC" -ForegroundColor Yellow
        Write-Host "   or: .\run-local.ps1 offline BTC" -ForegroundColor Yellow
        exit 1
    }
    python local_runner.py $ReportType $Symbol
}
else {
    python local_runner.py $ReportType
}

Write-Host ""
Write-Host "✅ Done!" -ForegroundColor Green
