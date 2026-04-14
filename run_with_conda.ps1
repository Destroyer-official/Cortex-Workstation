# PowerShell script to run Cortex Cleaner with Conda Python
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Cortex Cleaner - Starting with Conda Python" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$condaPython = "D:\program_software\conda\python.exe"
if (-not (Test-Path $condaPython)) {
    # Fallback to python in PATH
    $condaPython = "python"
    try {
        $pythonPath = Get-Command python -ErrorAction Stop | Select-Object -ExpandProperty Source
        Write-Host "Conda Python not found at default location. Falling back to PATH: $pythonPath" -ForegroundColor Yellow
    } catch {
        Write-Host "ERROR: python not found in PATH." -ForegroundColor Red
        Write-Host "Please ensure you have activated your conda environment or python is in your PATH." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "Using Conda Python at: $condaPython" -ForegroundColor Green
}

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