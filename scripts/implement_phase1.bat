@echo off
REM Phase 1 Implementation Script for Windows
REM Run this from the project root

echo ========================================
echo Cortex Cleaner - Phase 1 Implementation
echo ========================================
echo.

cd /d "%~dp0..\.."

echo Current directory: %CD%
echo.

echo Running implementation script...
python src\cortex_unified\implement_phase1.py

pause
