@echo off
REM ================================================
REM  Conflict Flagger - Windows Build Script
REM  Creates: dist\ConflictFlaggerAEC.exe (single file)
REM ================================================
REM
REM INSTRUCTIONS FOR INTERN:
REM 1. Install Python 3.11 from https://www.python.org/downloads/
REM    (Check "Add to PATH" during installation!)
REM 2. Open Command Prompt in this folder
REM 3. Run: build_windows.bat
REM 4. Result: dist\ConflictFlaggerAEC.exe
REM
REM ================================================

echo.
echo ==========================================
echo   Conflict Flagger - Windows Build
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.11 from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Install dependencies
echo.
echo Installing dependencies...
pip install --upgrade pip --quiet
pip install pyinstaller openpyxl pillow tkinterdnd2 ifcopenshell --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed

REM Clean previous build
echo.
echo Cleaning previous builds...
if exist "dist\ConflictFlaggerAEC.exe" del /f "dist\ConflictFlaggerAEC.exe"
if exist "build\conflict_flagger_onefile" rmdir /s /q "build\conflict_flagger_onefile"

REM Build
echo.
echo Building ConflictFlaggerAEC.exe...
echo (This may take a few minutes)
echo.

python -m PyInstaller --clean --noconfirm conflict_flagger_onefile.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

if not exist "dist\ConflictFlaggerAEC.exe" (
    echo.
    echo [ERROR] Build completed but exe not found!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Output: dist\ConflictFlaggerAEC.exe
echo.
for %%A in ("dist\ConflictFlaggerAEC.exe") do echo Size: %%~zA bytes
echo.
echo You can now distribute this single .exe file.
echo.
pause
