@echo off
REM Build Windows .exe natively on Windows
REM Usage: build_windows.bat

echo ==========================================
echo Conflict Flagger AEC - Windows Build
echo ==========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Download from: https://www.python.org/downloads/
    exit /b 1
)

REM Install dependencies if needed
echo Installing dependencies...
pip install --upgrade pip
pip install pyinstaller openpyxl pillow tkinterdnd2 ifcopenshell

REM Clean previous builds
echo Cleaning previous builds...
rmdir /s /q build\ConflictFlaggerAEC 2>nul
rmdir /s /q dist\ConflictFlaggerAEC 2>nul

REM Build using spec file (includes logo and optimizations)
echo Building Windows executable...
python -m PyInstaller --clean --noconfirm conflict_flagger.spec

if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

echo.
echo ==========================================
echo BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Windows executable: dist\ConflictFlaggerAEC\ConflictFlaggerAEC.exe
echo.
echo To distribute, copy the entire ConflictFlaggerAEC folder.

pause
