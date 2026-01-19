# Schedule Crypto Daily Report - Windows Task Scheduler Setup
# This script creates scheduled tasks to run the daily report twice a day (5 AM and 5 PM)

$TaskNameAM = "CryptoDailyReport_AM"
$TaskNamePM = "CryptoDailyReport_PM"
$TaskDescriptionAM = "Runs crypto daily report (morning) with fresh market data analysis"
$TaskDescriptionPM = "Runs crypto daily report (evening) with fresh market data analysis"
$ScriptPath = $PSScriptRoot
$WrapperScriptAM = Join-Path $ScriptPath "run-daily-task.ps1"
$WrapperScriptPM = Join-Path $ScriptPath "run-daily-task-pm.ps1"
$PythonScriptPath = Join-Path $ScriptPath "local_runner.py"
$VenvPython = Join-Path $ScriptPath ".venv\Scripts\python.exe"

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Gray
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Gray
    Write-Host "  3. Run this script again" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   📅 Crypto Daily Report - Task Scheduler Setup" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verify paths exist
if (-not (Test-Path $WrapperScriptAM)) {
    Write-Host "❌ Error: run-daily-task.ps1 not found at: $WrapperScriptAM" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $PythonScriptPath)) {
    Write-Host "❌ Error: local_runner.py not found at: $PythonScriptPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Error: Python virtual environment not found at: $VenvPython" -ForegroundColor Red
    Write-Host "Please create virtual environment first: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found AM wrapper: $WrapperScriptAM" -ForegroundColor Green
Write-Host "✓ Found script: $PythonScriptPath" -ForegroundColor Green
Write-Host "✓ Found Python: $VenvPython" -ForegroundColor Green
Write-Host ""

# Check if tasks already exist
$ExistingTaskAM = Get-ScheduledTask -TaskName $TaskNameAM -ErrorAction SilentlyContinue
$ExistingTaskPM = Get-ScheduledTask -TaskName $TaskNamePM -ErrorAction SilentlyContinue
# Also check for legacy single task
$LegacyTask = Get-ScheduledTask -TaskName "CryptoDailyReport" -ErrorAction SilentlyContinue

if ($ExistingTaskAM -or $ExistingTaskPM -or $LegacyTask) {
    Write-Host "⚠️  Existing crypto report tasks found!" -ForegroundColor Yellow
    if ($ExistingTaskAM) { Write-Host "  - $TaskNameAM" -ForegroundColor Gray }
    if ($ExistingTaskPM) { Write-Host "  - $TaskNamePM" -ForegroundColor Gray }
    if ($LegacyTask) { Write-Host "  - CryptoDailyReport (legacy)" -ForegroundColor Gray }
    $response = Read-Host "Do you want to remove and recreate them? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        if ($ExistingTaskAM) { Unregister-ScheduledTask -TaskName $TaskNameAM -Confirm:$false }
        if ($ExistingTaskPM) { Unregister-ScheduledTask -TaskName $TaskNamePM -Confirm:$false }
        if ($LegacyTask) { Unregister-ScheduledTask -TaskName "CryptoDailyReport" -Confirm:$false }
        Write-Host "✓ Removed existing tasks" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Setup cancelled" -ForegroundColor Red
        exit 0
    }
}

# Create scheduled task action for AM - Use PowerShell wrapper for better logging
$ActionAM = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperScriptAM`"" `
    -WorkingDirectory $ScriptPath

# Create scheduled task action for PM
$ActionPM = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperScriptPM`"" `
    -WorkingDirectory $ScriptPath

# Create triggers - AM at 5:00 AM, PM at 5:00 PM
$TriggerAM = New-ScheduledTaskTrigger -Daily -At "05:00AM"
$TriggerPM = New-ScheduledTaskTrigger -Daily -At "05:00PM"

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Get current user
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

# Register the AM task
try {
    Register-ScheduledTask `
        -TaskName $TaskNameAM `
        -Description $TaskDescriptionAM `
        -Action $ActionAM `
        -Trigger $TriggerAM `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null
    
    # Register the PM task
    Register-ScheduledTask `
        -TaskName $TaskNamePM `
        -Description $TaskDescriptionPM `
        -Action $ActionPM `
        -Trigger $TriggerPM `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "   ✅ Tasks Scheduled Successfully!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📋 Task Details:" -ForegroundColor Cyan
    Write-Host "  Morning Task:  $TaskNameAM" -ForegroundColor Gray
    Write-Host "  Evening Task:  $TaskNamePM" -ForegroundColor Gray
    Write-Host "  AM Schedule:   Daily at 5:00 AM" -ForegroundColor Gray
    Write-Host "  PM Schedule:   Daily at 5:00 PM" -ForegroundColor Gray
    Write-Host "  User:          $env:USERNAME" -ForegroundColor Gray
    Write-Host "  Script:        $PythonScriptPath" -ForegroundColor Gray
    Write-Host "  Python:        $VenvPython" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔍 What happens at 5:00 AM and 5:00 PM daily:" -ForegroundColor Cyan
    Write-Host "  1. Updates latest market data from Binance (cached if already fetched)" -ForegroundColor Gray
    Write-Host "  2. Calculates fresh RSI, MA, MACD indicators" -ForegroundColor Gray
    Write-Host "  3. Fetches live derivatives and order book data" -ForegroundColor Gray
    Write-Host "  4. Generates AI analysis with recent 12h news" -ForegroundColor Gray
    Write-Host "  5. Sends report to Telegram" -ForegroundColor Gray
    Write-Host "  6. Creates EPUB and emails to Kindle" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 For accurate CVD data, also run:" -ForegroundColor Yellow
    Write-Host "  .\setup-cvd-schedule.ps1  # Schedules CVD updates every 4 hours" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
    Write-Host "  Check status:   .\check-task-status.ps1" -ForegroundColor Gray
    Write-Host "  View log:       Get-Content task_runner.log -Tail 50" -ForegroundColor Gray
    Write-Host "  Live log:       Get-Content task_runner.log -Wait -Tail 50" -ForegroundColor Gray
    Write-Host "  Run AM now:     Start-ScheduledTask -TaskName '$TaskNameAM'" -ForegroundColor Gray
    Write-Host "  Run PM now:     Start-ScheduledTask -TaskName '$TaskNamePM'" -ForegroundColor Gray
    Write-Host "  View tasks:     Get-ScheduledTask -TaskName 'CryptoDailyReport*'" -ForegroundColor Gray
    Write-Host "  Disable AM:     Disable-ScheduledTask -TaskName '$TaskNameAM'" -ForegroundColor Gray
    Write-Host "  Disable PM:     Disable-ScheduledTask -TaskName '$TaskNamePM'" -ForegroundColor Gray
    Write-Host "  Remove AM:      Unregister-ScheduledTask -TaskName '$TaskNameAM'" -ForegroundColor Gray
    Write-Host "  Remove PM:      Unregister-ScheduledTask -TaskName '$TaskNamePM'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 To test a task now, run:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskNameAM'" -ForegroundColor White
    Write-Host "  .\check-task-status.ps1  # Check if it's running" -ForegroundColor White
    Write-Host ""
    
}
catch {
    Write-Host ""
    Write-Host "❌ Failed to create scheduled task!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}
