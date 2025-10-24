# Test the daily report directly in your current terminal
# This runs the report with live output so you can see what's happening

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   📊 Running Daily Report (Direct Test)" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$VenvPython = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Python virtual environment not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Starting report generation with live output..." -ForegroundColor Yellow
Write-Host ""

# Run with live output
& $VenvPython local_runner.py daily

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "   ✅ Report completed successfully!" -ForegroundColor Green
}
else {
    Write-Host "   ❌ Report failed with exit code: $exitCode" -ForegroundColor Red
}
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
