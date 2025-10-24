# Wrapper script for running the daily report from Task Scheduler
# This ensures proper logging and error handling

$ScriptPath = $PSScriptRoot
$VenvPython = Join-Path $ScriptPath ".venv\Scripts\python.exe"
$PythonScript = Join-Path $ScriptPath "local_runner.py"
$LogFile = Join-Path $ScriptPath "task_runner.log"

# Redirect output to log file
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

try {
    Add-Content -Path $LogFile -Value "=========================================="
    Add-Content -Path $LogFile -Value "Task started: $timestamp"
    Add-Content -Path $LogFile -Value "Working directory: $ScriptPath"
    Add-Content -Path $LogFile -Value "Python: $VenvPython"
    Add-Content -Path $LogFile -Value "Script: $PythonScript"
    Add-Content -Path $LogFile -Value "=========================================="
    
    # Change to script directory
    Set-Location $ScriptPath
    
    # Run the Python script and capture output
    & $VenvPython $PythonScript "daily" 2>&1 | Tee-Object -FilePath $LogFile -Append
    
    $exitCode = $LASTEXITCODE
    $endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Add-Content -Path $LogFile -Value "=========================================="
    Add-Content -Path $LogFile -Value "Task ended: $endTime"
    Add-Content -Path $LogFile -Value "Exit code: $exitCode"
    Add-Content -Path $LogFile -Value "=========================================="
    
    exit $exitCode
    
}
catch {
    $errorTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "=========================================="
    Add-Content -Path $LogFile -Value "ERROR at $errorTime"
    Add-Content -Path $LogFile -Value "Error: $_"
    Add-Content -Path $LogFile -Value "=========================================="
    exit 1
}
