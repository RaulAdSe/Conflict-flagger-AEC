#!/usr/bin/env python3
"""
Build script for Conflict Flagger AEC Desktop Application

This script builds the application for the current platform:
- Windows: Creates ConflictFlaggerAEC.exe in dist/
- macOS: Creates Conflict Flagger AEC.app in dist/

Usage:
    python build_app.py [--clean]

Options:
    --clean     Remove build artifacts before building
"""

import subprocess
import sys
import shutil
from pathlib import Path


def clean_build_dirs():
    """Remove previous build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Cleaning {dir_name}/...")
            shutil.rmtree(dir_path)

    # Remove .spec generated files (keep our spec)
    for spec_file in Path('.').glob('*.spec'):
        if spec_file.name != 'conflict_flagger.spec':
            spec_file.unlink()


def check_dependencies():
    """Check and install required dependencies."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Check other dependencies
    required = ['ifcopenshell', 'openpyxl']
    for package in required:
        try:
            __import__(package)
            print(f"{package}: OK")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


def build_app():
    """Build the application using PyInstaller."""
    print(f"\nBuilding for platform: {sys.platform}")
    print("=" * 50)

    # Run PyInstaller with our spec file
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'conflict_flagger.spec'
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    if result.returncode != 0:
        print("\nBuild failed!")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("BUILD SUCCESSFUL!")
    print("=" * 50)

    # Show output location
    dist_path = Path('dist')
    if sys.platform == 'darwin':
        app_path = dist_path / 'Conflict Flagger AEC.app'
        if app_path.exists():
            print(f"\nmacOS App: {app_path.absolute()}")
            print("\nTo run: open 'dist/Conflict Flagger AEC.app'")
    else:
        exe_path = dist_path / 'ConflictFlaggerAEC.exe'
        if exe_path.exists():
            print(f"\nWindows EXE: {exe_path.absolute()}")
            print(f"\nTo run: dist\\ConflictFlaggerAEC.exe")


def main():
    """Main entry point."""
    print("Conflict Flagger AEC - Build Script")
    print("=" * 50)

    # Check for --clean flag
    if '--clean' in sys.argv:
        clean_build_dirs()

    # Check dependencies
    print("\nChecking dependencies...")
    check_dependencies()

    # Build
    build_app()


if __name__ == '__main__':
    main()
