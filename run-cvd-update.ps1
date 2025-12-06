# Run CVD (Cumulative Volume Delta) hourly update
# This script fetches new trades and updates hourly CVD snapshots

$ErrorActionPreference = "Stop"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ScriptPath ".venv\Scripts\python.exe"
$LogFile = Join-Path $ScriptPath "cvd_update.log"

# Function to write to log
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "$Timestamp - $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    Write-Host $LogMessage
}

Write-Log "=========================================="
Write-Log "CVD Update Started"
Write-Log "=========================================="

# Change to script directory
Set-Location $ScriptPath

# Activate virtual environment and run CVD update
try {
    Write-Log "Running CVD update..."
    
    $PythonCode = @"
import os
import sys
sys.path.insert(0, r'$ScriptPath')
os.chdir(r'$ScriptPath')

# Set environment for local development
os.environ['DATABASE_TYPE'] = 'sqlite'

from source_repository import SymbolRepository
from infra.sql_connection import get_connection
from technical_analysis.order_book_report import fetch_cvd_report

# Get connection and symbols
conn = get_connection()
symbol_repo = SymbolRepository(conn)
symbols = symbol_repo.get_active_symbols()

print(f"Updating CVD for {len(symbols)} symbols...")

# Run CVD update (this will do incremental fetch)
table = fetch_cvd_report(symbols, conn)

print("CVD Update Complete!")
print(table)

conn.close()
"@
    
    # Run Python with the inline script
    $Result = & $VenvPython -c $PythonCode 2>&1
    
    foreach ($line in $Result) {
        Write-Log $line
    }
    
    Write-Log "CVD update completed successfully"
}
catch {
    Write-Log "ERROR: CVD update failed!"
    Write-Log "Error: $_"
    exit 1
}

Write-Log "=========================================="
Write-Log "CVD Update Finished"
Write-Log "=========================================="
