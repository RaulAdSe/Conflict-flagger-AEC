#!/bin/bash
# Build Conflict Flagger AEC for both macOS and Windows
# Usage: ./build_all.sh
#
# Creates:
#   dist/Flagger.app              - macOS application
#   dist/ConflictFlaggerAEC/      - Windows application (exe + dependencies)

set -e

echo "=============================================="
echo "  Conflict Flagger AEC - Build All Platforms"
echo "=============================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Clean dist folder
echo "Cleaning previous builds..."
rm -rf dist/Flagger.app dist/Flagger dist/ConflictFlaggerAEC 2>/dev/null || true
rm -rf build 2>/dev/null || true
print_status "Cleaned previous builds"
echo ""

# ============================================
# BUILD macOS APP
# ============================================
echo "=============================================="
echo "  Building macOS Application"
echo "=============================================="
echo ""

if command -v python3 &> /dev/null; then
    echo "Building macOS .app..."
    python3 -m PyInstaller --clean --noconfirm conflict_flagger.spec

    if [ -d "dist/Flagger.app" ]; then
        print_status "macOS build complete: dist/Flagger.app"
        MACOS_SIZE=$(du -sh dist/Flagger.app | cut -f1)
        echo "    Size: $MACOS_SIZE"
    else
        print_error "macOS build failed"
    fi
else
    print_error "Python3 not found - skipping macOS build"
fi

echo ""

# ============================================
# BUILD Windows EXE (via Wine)
# ============================================
echo "=============================================="
echo "  Building Windows Application (via Wine)"
echo "=============================================="
echo ""

WINE_PYTHON="C:\\Program Files\\Python311\\python.exe"

if command -v wine &> /dev/null; then
    # Check if Python is installed in Wine
    if wine "$WINE_PYTHON" --version &> /dev/null 2>&1; then
        echo "Building Windows .exe..."

        # Suppress Wine debug messages
        export WINEDEBUG=-all

        # Use spec file for consistent builds with logo and optimizations
        wine "$WINE_PYTHON" -m PyInstaller \
            --clean \
            --noconfirm \
            conflict_flagger.spec 2>&1 | grep -E "(INFO: Build|ERROR|Building|completed)"

        if [ -f "dist/ConflictFlaggerAEC/ConflictFlaggerAEC.exe" ]; then
            print_status "Windows build complete: dist/ConflictFlaggerAEC/"
            WIN_SIZE=$(du -sh dist/ConflictFlaggerAEC | cut -f1)
            echo "    Size: $WIN_SIZE"
        else
            print_error "Windows build failed"
        fi
    else
        print_warning "Python not installed in Wine"
        echo "    To install: See docs/BUILD.md"
        echo "    Quick install:"
        echo "      curl -L -o /tmp/python-3.11.9-amd64.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
        echo "      wine /tmp/python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1"
    fi
else
    print_warning "Wine not installed - skipping Windows build"
    echo "    To install: brew install --cask wine-stable"
fi

echo ""

# ============================================
# CREATE DISTRIBUTION PACKAGES
# ============================================
echo "=============================================="
echo "  Creating Distribution Packages"
echo "=============================================="
echo ""

# macOS: Create compressed DMG (ULMO = lzma compression)
if [ -d "dist/Flagger.app" ]; then
    echo "Creating macOS DMG..."
    rm -f dist/Flagger.dmg 2>/dev/null
    hdiutil create -volname "Flagger" -srcfolder dist/Flagger.app -ov -format ULMO dist/Flagger.dmg -quiet
    if [ -f "dist/Flagger.dmg" ]; then
        print_status "macOS DMG created: dist/Flagger.dmg ($(du -sh dist/Flagger.dmg | cut -f1))"
    fi
fi

# Windows: Create compressed ZIP
if [ -d "dist/ConflictFlaggerAEC" ]; then
    echo "Creating Windows ZIP..."
    rm -f dist/ConflictFlagger-Windows.zip 2>/dev/null
    (cd dist && zip -r -9 -q ConflictFlagger-Windows.zip ConflictFlaggerAEC/)
    if [ -f "dist/ConflictFlagger-Windows.zip" ]; then
        print_status "Windows ZIP created: dist/ConflictFlagger-Windows.zip ($(du -sh dist/ConflictFlagger-Windows.zip | cut -f1))"
    fi
fi

echo ""

# ============================================
# SUMMARY
# ============================================
echo "=============================================="
echo "  Build Summary"
echo "=============================================="
echo ""

if [ -d "dist/Flagger.app" ]; then
    print_status "macOS:   dist/Flagger.app ($(du -sh dist/Flagger.app | cut -f1))"
else
    print_error "macOS:   Not built"
fi

if [ -f "dist/ConflictFlaggerAEC/ConflictFlaggerAEC.exe" ]; then
    print_status "Windows: dist/ConflictFlaggerAEC/ ($(du -sh dist/ConflictFlaggerAEC | cut -f1))"
else
    print_error "Windows: Not built"
fi

echo ""
echo "Distribution packages (for sharing):"
if [ -f "dist/Flagger.dmg" ]; then
    print_status "macOS:   dist/Flagger.dmg ($(du -sh dist/Flagger.dmg | cut -f1))"
fi
if [ -f "dist/ConflictFlagger-Windows.zip" ]; then
    print_status "Windows: dist/ConflictFlagger-Windows.zip ($(du -sh dist/ConflictFlagger-Windows.zip | cut -f1))"
fi

echo ""
echo "=============================================="
echo "  Done!"
echo "=============================================="
