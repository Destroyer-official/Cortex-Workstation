# PowerShell script to run Cortex Cleaner with Conda Python
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Cortex Cleaner - Starting with Conda Python" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$condaPython = if ($env:CONDA_PREFIX -and (Test-Path "$env:CONDA_PREFIX\python.exe")) {
    "$env:CONDA_PREFIX\python.exe"
} else {
    try {
        (Get-Command python -ErrorAction Stop).Source
    } catch {
        $null
    }
}

if (-not $condaPython) {
    Write-Host "ERROR: python not found in PATH or active Conda environment." -ForegroundColor Red
    Write-Host "Please ensure you have activated your conda environment or python is in your PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using Python at: $condaPython" -ForegroundColor Green

Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""


# Run the application
Write-Host ""
Write-Host "Starting Cortex Cleaner..." -ForegroundColor Yellow
& $condaPython "run_gui.py"

# Keep window open if there was an error
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Application exited with error code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}