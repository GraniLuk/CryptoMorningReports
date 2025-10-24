# Quick script to check for errors in the task log
# Shows only error-related lines for fast troubleshooting

$LogFile = "task_runner.log"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   🔍 Error Check - Daily Report Task" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $LogFile)) {
    Write-Host "❌ Log file not found: $LogFile" -ForegroundColor Red
    Write-Host "   Run the task first to generate logs." -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Get last run info from Task Scheduler
$Task = Get-ScheduledTask -TaskName "CryptoDailyReport" -ErrorAction SilentlyContinue
if ($Task) {
    $TaskInfo = Get-ScheduledTaskInfo -TaskName "CryptoDailyReport"
    Write-Host "📋 Last Run: $($TaskInfo.LastRunTime)" -ForegroundColor Gray
    
    if ($TaskInfo.LastTaskResult -eq 0) {
        Write-Host "📋 Last Result: ✅ Success (0)" -ForegroundColor Green
    }
    elseif ($TaskInfo.LastTaskResult -eq 267009) {
        Write-Host "📋 Last Result: ⏳ Running (267009)" -ForegroundColor Yellow
    }
    else {
        Write-Host "📋 Last Result: ❌ Error ($($TaskInfo.LastTaskResult))" -ForegroundColor Red
    }
    Write-Host ""
}

# Search for errors, exceptions, failures
$ErrorPatterns = @(
    "ERROR",
    "Error:",
    "Exception",
    "Traceback",
    "Failed",
    "failed",
    "Exit code: [1-9]",  # Non-zero exit codes
    "CRITICAL"
)

$ErrorsFound = @()

foreach ($pattern in $ErrorPatterns) {
    $foundMatches = Select-String -Path $LogFile -Pattern $pattern -Context 2, 1
    if ($foundMatches) {
        $ErrorsFound += $foundMatches
    }
}

if ($ErrorsFound.Count -eq 0) {
    Write-Host "✅ No errors found in log file!" -ForegroundColor Green
    Write-Host ""
    
    # Show last completion
    $LastCompletion = Select-String -Path $LogFile -Pattern "Task ended:" | Select-Object -Last 1
    if ($LastCompletion) {
        Write-Host "Last successful completion:" -ForegroundColor Gray
        Write-Host "  $($LastCompletion.Line)" -ForegroundColor Gray
    }
    
    $ExitCode = Select-String -Path $LogFile -Pattern "Exit code:" | Select-Object -Last 1
    if ($ExitCode) {
        Write-Host "  $($ExitCode.Line)" -ForegroundColor Gray
    }
    Write-Host ""
}
else {
    Write-Host "⚠️  Found $($ErrorsFound.Count) potential issues:" -ForegroundColor Red
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host ""
    
    # Group by unique errors and show last occurrence of each
    $UniqueErrors = $ErrorsFound | Select-Object -Last 20
    
    foreach ($errorLine in $UniqueErrors) {
        Write-Host "Line $($errorLine.LineNumber):" -ForegroundColor Yellow
        
        # Show context before
        if ($errorLine.Context.PreContext) {
            $errorLine.Context.PreContext | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        
        # Show the error line itself
        Write-Host "  $($errorLine.Line)" -ForegroundColor Red
        
        # Show context after
        if ($errorLine.Context.PostContext) {
            $errorLine.Context.PostContext | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        
        Write-Host ""
    }
    
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 To view full log: Get-Content $LogFile | more" -ForegroundColor Yellow
    Write-Host "💡 To view all errors: Select-String -Path $LogFile -Pattern 'ERROR|Exception' -Context 3" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
