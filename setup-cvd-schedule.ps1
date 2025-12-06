# Schedule CVD Updates - Windows Task Scheduler Setup
# This script creates scheduled tasks to update CVD data multiple times per day
# for accurate 1h/4h/24h CVD accumulation

$TaskName = "CryptoCVDUpdate"
$TaskDescription = "Updates CVD (Cumulative Volume Delta) hourly snapshots for accurate order flow tracking"
$ScriptPath = $PSScriptRoot
$WrapperScript = Join-Path $ScriptPath "run-cvd-update.ps1"
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
Write-Host "   📊 CVD Update - Task Scheduler Setup" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verify paths exist
if (-not (Test-Path $WrapperScript)) {
    Write-Host "❌ Error: run-cvd-update.ps1 not found at: $WrapperScript" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Error: Python virtual environment not found at: $VenvPython" -ForegroundColor Red
    Write-Host "Please create virtual environment first: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found wrapper: $WrapperScript" -ForegroundColor Green
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

# Create scheduled task action
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperScript`"" `
    -WorkingDirectory $ScriptPath

# Create multiple triggers - every 4 hours for good 24h coverage
# This ensures we have fresh data for 1h, 4h, and 24h windows
$Triggers = @(
    (New-ScheduledTaskTrigger -Daily -At "00:00AM"),  # Midnight
    (New-ScheduledTaskTrigger -Daily -At "04:00AM"),  # 4 AM (before daily report)
    (New-ScheduledTaskTrigger -Daily -At "08:00AM"),  # 8 AM
    (New-ScheduledTaskTrigger -Daily -At "12:00PM"),  # Noon
    (New-ScheduledTaskTrigger -Daily -At "04:00PM"),  # 4 PM
    (New-ScheduledTaskTrigger -Daily -At "08:00PM")   # 8 PM
)

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

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
        -Trigger $Triggers `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "   ✅ CVD Update Task Scheduled Successfully!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📋 Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:        $TaskName" -ForegroundColor Gray
    Write-Host "  User:        $env:USERNAME" -ForegroundColor Gray
    Write-Host "  Script:      $WrapperScript" -ForegroundColor Gray
    Write-Host ""
    Write-Host "⏰ Schedule (6 times daily):" -ForegroundColor Cyan
    Write-Host "  • 12:00 AM (midnight)" -ForegroundColor Gray
    Write-Host "  • 04:00 AM (before daily report)" -ForegroundColor Gray
    Write-Host "  • 08:00 AM" -ForegroundColor Gray
    Write-Host "  • 12:00 PM (noon)" -ForegroundColor Gray
    Write-Host "  • 04:00 PM" -ForegroundColor Gray
    Write-Host "  • 08:00 PM" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📊 What each update does:" -ForegroundColor Cyan
    Write-Host "  1. Fetches NEW trades since last update (incremental)" -ForegroundColor Gray
    Write-Host "  2. Buckets trades by hour" -ForegroundColor Gray
    Write-Host "  3. Saves hourly CVD snapshots to database" -ForegroundColor Gray
    Write-Host "  4. Cleans up snapshots older than 48 hours" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 Benefits:" -ForegroundColor Cyan
    Write-Host "  • Accurate 1h/4h/24h CVD from accumulated hourly data" -ForegroundColor Gray
    Write-Host "  • Light API usage (only fetches new trades)" -ForegroundColor Gray
    Write-Host "  • Daily report at 4AM will have full 24h of CVD data" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
    Write-Host "  View log:       Get-Content cvd_update.log -Tail 50" -ForegroundColor Gray
    Write-Host "  Run now:        Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  View task:      Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Disable task:   Disable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Remove task:    Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 To test the task now, run:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    
}
catch {
    Write-Host ""
    Write-Host "❌ Failed to create scheduled task!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}
