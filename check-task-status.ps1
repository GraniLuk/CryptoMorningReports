# Check Crypto Daily Report Task Status
# This script shows the current status of the scheduled task and helps you view logs

$TaskName = "CryptoDailyReport"
$LogFile = "app.log"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   📊 Crypto Daily Report - Task Status" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Get task info
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $Task) {
    Write-Host "❌ Task '$TaskName' not found!" -ForegroundColor Red
    Write-Host "Run .\setup-daily-schedule.ps1 to create it." -ForegroundColor Yellow
    exit 1
}

$TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

# Display task status
Write-Host "📋 Task Status:" -ForegroundColor Cyan
Write-Host "  State:           $($Task.State)" -ForegroundColor $(if ($Task.State -eq "Running") { "Yellow" } else { "Gray" })
Write-Host "  Last Run:        $($TaskInfo.LastRunTime)" -ForegroundColor Gray
Write-Host "  Next Run:        $($TaskInfo.NextRunTime)" -ForegroundColor Gray
Write-Host "  Missed Runs:     $($TaskInfo.NumberOfMissedRuns)" -ForegroundColor Gray

# Interpret last result
$LastResult = $TaskInfo.LastTaskResult
if ($LastResult -eq 0) {
    Write-Host "  Last Result:     Success (0)" -ForegroundColor Green
}
elseif ($LastResult -eq 267009) {
    Write-Host "  Last Result:     Running (267009)" -ForegroundColor Yellow
}
elseif ($LastResult -eq 267011) {
    Write-Host "  Last Result:     Task not yet run (267011)" -ForegroundColor Gray
}
else {
    Write-Host "  Last Result:     Error ($LastResult)" -ForegroundColor Red
}

Write-Host ""

# Check if log file exists
if (Test-Path $LogFile) {
    $LogSize = (Get-Item $LogFile).Length
    $LogSizeKB = [math]::Round($LogSize / 1KB, 2)
    
    Write-Host "📄 Log File: $LogFile ($LogSizeKB KB)" -ForegroundColor Cyan
    Write-Host ""
    
    # Check for errors in recent log entries
    $RecentLines = Get-Content $LogFile -Tail 100
    $ErrorLines = $RecentLines | Select-String -Pattern "ERROR|Exception|Traceback|Failed|failed" -SimpleMatch
    
    if ($ErrorLines) {
        Write-Host "⚠️  ERRORS FOUND in recent logs:" -ForegroundColor Red
        Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
        $ErrorLines | Select-Object -First 10 | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
        Write-Host ""
    }
    
    # Show tail of log
    Write-Host "📜 Last 30 lines of log:" -ForegroundColor Yellow
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Get-Content $LogFile -Tail 30
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "💡 To view full log: Get-Content $LogFile" -ForegroundColor DarkGray
    Write-Host "💡 To tail log live: Get-Content $LogFile -Wait -Tail 50" -ForegroundColor DarkGray
    Write-Host "💡 To search errors: Select-String -Path $LogFile -Pattern 'ERROR|Exception'" -ForegroundColor DarkGray
}
else {
    Write-Host "ℹ️  Log file not found: $LogFile" -ForegroundColor Yellow
    Write-Host "   The task may not have started writing logs yet." -ForegroundColor Gray
}

Write-Host ""
Write-Host "📝 Quick Commands:" -ForegroundColor Cyan
Write-Host "  Start task:     Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Stop task:      Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  View this:      .\check-task-status.ps1" -ForegroundColor Gray
Write-Host "  Live log:       Get-Content $LogFile -Wait -Tail 50" -ForegroundColor Gray
Write-Host ""
