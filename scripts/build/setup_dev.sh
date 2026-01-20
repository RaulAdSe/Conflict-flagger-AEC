#!/bin/bash
# =============================================================================
# Conflict Flagger AEC - Development Setup
# =============================================================================
#
# This script sets up your development environment on macOS.
#
# YOU NEED TWO VIRTUAL ENVIRONMENTS:
#
#   venv/       - Mac Python (for running tests, development, building .app)
#   venv_win/   - Wine Python (for building Windows .exe on your Mac)
#
# WHY TWO VENVS?
# - venv/ uses your Mac's Python - this is where you develop and test
# - venv_win/ uses Python running inside Wine (Windows emulator)
#   This lets you build a real Windows .exe without needing a Windows PC
#
# =============================================================================

set -e  # Exit on any error

echo "=============================================="
echo "  Conflict Flagger AEC - Development Setup"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# STEP 1: Mac Python venv (for development & testing)
# -----------------------------------------------------------------------------
echo "STEP 1: Setting up Mac Python venv..."
echo "--------------------------------------"

if [ -d "venv" ]; then
    echo "  venv/ already exists, skipping..."
else
    echo "  Creating venv/..."
    python3 -m venv venv
    echo "  Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install pyinstaller pillow tkinterdnd2
    deactivate
    echo "  Done!"
fi

echo ""

# -----------------------------------------------------------------------------
# STEP 2: Wine Python venv (for building Windows .exe)
# -----------------------------------------------------------------------------
echo "STEP 2: Setting up Wine Python venv..."
echo "---------------------------------------"

# Check if Wine is installed
if ! command -v wine &> /dev/null; then
    echo "  ERROR: Wine is not installed!"
    echo ""
    echo "  Install Wine first:"
    echo "    brew install --cask wine-stable"
    echo ""
    echo "  Then install Python inside Wine:"
    echo "    curl -O https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    echo "    wine python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1"
    echo ""
    exit 1
fi

# Check if Python is available in Wine
if ! wine python --version &> /dev/null 2>&1; then
    echo "  ERROR: Python is not installed in Wine!"
    echo ""
    echo "  Install Python inside Wine:"
    echo "    curl -O https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    echo "    wine python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1"
    echo ""
    exit 1
fi

if [ -d "venv_win" ]; then
    echo "  venv_win/ already exists, skipping..."
else
    echo "  Creating venv_win/ (this uses Wine Python)..."
    wine python -m venv venv_win 2>/dev/null
    echo "  Installing dependencies in Wine..."
    wine venv_win/Scripts/pip.exe install --upgrade pip 2>/dev/null
    wine venv_win/Scripts/pip.exe install -r requirements.txt 2>/dev/null
    wine venv_win/Scripts/pip.exe install pyinstaller pillow tkinterdnd2 2>/dev/null
    echo "  Done!"
fi

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Your two virtual environments:"
echo ""
echo "  venv/        - Mac Python (development & tests)"
echo "                 Activate: source venv/bin/activate"
echo ""
echo "  venv_win/    - Wine Python (building .exe)"
echo "                 Used by: wine venv_win/Scripts/pyinstaller.exe"
echo ""
echo "Quick commands:"
echo ""
echo "  Run tests:       source venv/bin/activate && pytest tests/"
echo "  Build .exe:      wine venv_win/Scripts/pyinstaller.exe --clean --noconfirm conflict_flagger.spec"
echo "  Build .app:      source venv/bin/activate && pyinstaller --clean --noconfirm conflict_flagger.spec"
echo ""
