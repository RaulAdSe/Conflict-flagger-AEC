#!/bin/bash
# Build Windows .exe using Wine on macOS
# Usage: ./build_windows.sh

set -e

echo "=========================================="
echo "Conflict Flagger AEC - Windows Build"
echo "=========================================="

# Check if Wine is installed
if ! command -v wine &> /dev/null; then
    echo "Error: Wine is not installed."
    echo "Install with: brew install --cask wine-stable"
    exit 1
fi

# Check if Python is installed in Wine
WINE_PYTHON="C:\\Program Files\\Python311\\python.exe"
if ! wine "$WINE_PYTHON" --version &> /dev/null 2>&1; then
    echo "Error: Python not found in Wine."
    echo "Install Python 3.11 for Windows in Wine first."
    echo "See docs/BUILD.md for instructions."
    exit 1
fi

echo "Using Wine Python: $WINE_PYTHON"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ConflictFlaggerAEC dist/ConflictFlaggerAEC 2>/dev/null || true

# Build
echo "Building Windows executable..."
wine "$WINE_PYTHON" -m PyInstaller \
    --clean \
    --noconfirm \
    --name ConflictFlaggerAEC \
    --windowed \
    --onedir \
    src/app_comparator.py

echo ""
echo "=========================================="
echo "BUILD SUCCESSFUL!"
echo "=========================================="
echo ""
echo "Windows executable: dist/ConflictFlaggerAEC/ConflictFlaggerAEC.exe"
echo "Size: $(du -sh dist/ConflictFlaggerAEC | cut -f1)"
