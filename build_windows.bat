@echo off
REM Build script for Windows - Creates ConflictFlaggerAEC.exe
REM Run this from the project root directory

echo ====================================================
echo Conflict Flagger AEC - Windows Build Script
echo ====================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Build the application
echo.
echo Building Windows executable...
python build_app.py --clean

echo.
echo ====================================================
echo Build complete! Check dist\ConflictFlaggerAEC.exe
echo ====================================================
pause
