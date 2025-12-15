# PowerShell script to run Azure Function locally
# Usage: 
#   .\run-local.ps1                 # Daily report
#   .\run-local.ps1 current BTC     # Current situation report for BTC
#   .\run-local.ps1 weekly          # Weekly report
#   .\run-local.ps1 -LogLevel DEBUG # Set log level to DEBUG

param(
    [Parameter(Mandatory = $false)]
    [string]$ReportType = 'daily',
    
    [Parameter(Mandatory = $false)]
    [string]$Symbol = '',
    
    [Parameter(Mandatory = $false)]
    [string]$LogLevel = 'INFO'
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
Write-Host "🚀 Running $ReportType report..." -ForegroundColor Green
Write-Host ""

# Set logging level environment variable
$env:LOG_LEVEL = $LogLevel
Write-Host "📝 Log level set to: $LogLevel" -ForegroundColor Blue

# Run the local runner
# Normalize ReportType and support shorthand for AM/PM
$normalizedReportType = if ($null -ne $ReportType) { $ReportType.ToLower() } else { 'daily' }

# If user passes just AM or PM as the first argument, treat as daily report with run_id
if ($normalizedReportType -in @('am', 'pm')) {
    $runId = $normalizedReportType.ToUpper()
    Write-Host "🚀 Running daily report with run id: $runId" -ForegroundColor Green
    python local_runner.py daily $runId
    Write-Host "" 
    # Removed duplicate "✅ Done!" message
    exit 0
}

if ($normalizedReportType -eq 'current' -or ($normalizedReportType -eq 'offline' -and $Symbol)) {
    if ([string]::IsNullOrEmpty($Symbol)) {
        Write-Host "❌ Error: Symbol required" -ForegroundColor Red
        Write-Host "Usage: .\run-local.ps1 current BTC" -ForegroundColor Yellow
        Write-Host "   or: .\run-local.ps1 offline BTC" -ForegroundColor Yellow
        exit 1
    }
    python local_runner.py $normalizedReportType $Symbol
}
else {
    # For daily/weekly, allow passing AM/PM as second parameter
    if ($normalizedReportType -eq 'daily' -and -not [string]::IsNullOrEmpty($Symbol)) {
        $runIdCandidate = ($Symbol ?? '').ToUpper()
        if ($runIdCandidate -in @('AM', 'PM')) {
            python local_runner.py daily $runIdCandidate
        }
        else {
            # If second parameter is not AM/PM treat it as symbol for current report
            python local_runner.py daily
        }
    }
    else {
        python local_runner.py $normalizedReportType
    }
}

Write-Host ""
Write-Host "✅ Done!" -ForegroundColor Green
