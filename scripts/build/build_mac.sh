#!/bin/bash
# Build script for macOS - Creates Conflict Flagger AEC.app
# Run this from the project root directory

echo "===================================================="
echo "Conflict Flagger AEC - macOS Build Script"
echo "===================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt
pip3 install pyinstaller

# Build the application
echo ""
echo "Building macOS application..."
python3 build_app.py --clean

echo ""
echo "===================================================="
echo "Build complete! Check dist/Conflict Flagger AEC.app"
echo "===================================================="
echo ""
echo "To run: open 'dist/Conflict Flagger AEC.app'"
