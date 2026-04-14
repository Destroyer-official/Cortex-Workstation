@echo off
echo ========================================
echo    Cortex Cleaner - Starting with Conda Python
echo ========================================
echo.
echo Using Python: D:\program_software\conda\python.exe
echo Working Directory: %CD%
echo.

REM Find python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: python not found in PATH.
    echo Please ensure you have activated your conda environment or python is in your PATH.
    pause
    exit /b 1
)

REM Run the application
echo Starting application...
python run_gui.py

REM Keep window open if there was an error
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error code: %ERRORLEVEL%
    pause
)