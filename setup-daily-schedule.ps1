# Schedule Crypto Daily Report - Windows Task Scheduler Setup
# This script creates a scheduled task to run the daily report every day at 5:00 AM

$TaskName = "CryptoDailyReport"
$TaskDescription = "Runs crypto daily report with fresh market data analysis"
$ScriptPath = $PSScriptRoot
$WrapperScript = Join-Path $ScriptPath "run-daily-task.ps1"
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
if (-not (Test-Path $WrapperScript)) {
    Write-Host "❌ Error: run-daily-task.ps1 not found at: $WrapperScript" -ForegroundColor Red
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

Write-Host "✓ Found wrapper: $WrapperScript" -ForegroundColor Green
Write-Host "✓ Found script: $PythonScriptPath" -ForegroundColor Green
Write-Host "✓ Found Python: $VenvPython" -ForegroundColor Green
Write-Host ""

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "⚠️  Task '$TaskName' already exists!" -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove and recreate it? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "✓ Removed existing task" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Setup cancelled" -ForegroundColor Red
        exit 0
    }
}

# Create scheduled task action - Use PowerShell wrapper for better logging
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperScript`"" `
    -WorkingDirectory $ScriptPath

# Create trigger - Daily at 5:00 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At "05:00AM"

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

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "   ✅ Task Scheduled Successfully!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📋 Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:        $TaskName" -ForegroundColor Gray
    Write-Host "  Schedule:    Daily at 5:00 AM" -ForegroundColor Gray
    Write-Host "  User:        $env:USERNAME" -ForegroundColor Gray
    Write-Host "  Script:      $PythonScriptPath" -ForegroundColor Gray
    Write-Host "  Python:      $VenvPython" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔍 What happens at 5:00 AM daily:" -ForegroundColor Cyan
    Write-Host "  1. Updates latest 3 days of market data from Binance" -ForegroundColor Gray
    Write-Host "  2. Calculates fresh RSI, MA, MACD indicators" -ForegroundColor Gray
    Write-Host "  3. Generates AI analysis with real-time news" -ForegroundColor Gray
    Write-Host "  4. Sends report to Telegram" -ForegroundColor Gray
    Write-Host "  5. Creates EPUB and emails to Kindle" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
    Write-Host "  Check status:   .\check-task-status.ps1" -ForegroundColor Gray
    Write-Host "  View log:       Get-Content task_runner.log -Tail 50" -ForegroundColor Gray
    Write-Host "  Live log:       Get-Content task_runner.log -Wait -Tail 50" -ForegroundColor Gray
    Write-Host "  Run now:        Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  View task:      Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Disable task:   Disable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Enable task:    Enable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Remove task:    Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 To test the task now, run:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
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
