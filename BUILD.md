# Build Guide - Conflict Flagger AEC

This guide explains how to build the desktop application for **macOS** and **Windows**. Since you and your teammate use different operating systems, this document covers both workflows.

## Overview

The application uses **PyInstaller** to create standalone executables. The build configuration is in `conflict_flagger.spec`.

| Platform | Output | Build On |
|----------|--------|----------|
| macOS | `Flagger.app` (~413 MB) | Mac only |
| Windows | `ConflictFlaggerAEC.exe` (~67 MB) | Windows only |

**Important**: Each platform must be built on its native OS. You cannot cross-compile (e.g., build Windows .exe on Mac directly).

---

## Prerequisites

### Both Platforms

```bash
# 1. Clone the repository
git clone https://github.com/RaulAdSe/Conflict-flagger-AEC.git
cd Conflict-flagger-AEC

# 2. Create virtual environment (recommended)
python -m venv venv

# Activate it:
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install build tools
pip install pyinstaller pillow tkinterdnd2
```

### macOS Specific
- Python 3.10+ (via Homebrew or python.org)
- Xcode Command Line Tools: `xcode-select --install`

### Windows Specific
- Python 3.10+ from [python.org](https://www.python.org/downloads/)
- Add Python to PATH during installation

---

## Building for macOS (Your Mac)

### Quick Build

```bash
# From repository root
pyinstaller --clean --noconfirm conflict_flagger.spec
```

### Using the build script

```bash
python build_app.py --clean
```

### Output Location

```
dist/
└── Flagger.app/          # The macOS application bundle
    └── Contents/
        └── MacOS/
            └── Flagger   # The actual executable
```

### Testing the Build

```bash
# Run directly
./dist/Flagger.app/Contents/MacOS/Flagger

# Or open normally
open dist/Flagger.app
```

### Distribution

To share with other Mac users:
```bash
# Create a zip for distribution
cd dist
zip -r Flagger-macOS.zip Flagger.app
```

---

## Building for Windows (Your Teammate)

### Quick Build

```powershell
# From repository root (PowerShell or CMD)
pyinstaller --clean --noconfirm conflict_flagger.spec
```

### Using the build script

```powershell
python build_app.py --clean
```

### Alternative: Using the batch file

```powershell
.\build_windows.bat
```

### Output Location

```
dist/
└── ConflictFlaggerAEC.exe    # Single-file Windows executable
```

### Testing the Build

Double-click `ConflictFlaggerAEC.exe` or run from command line:
```powershell
.\dist\ConflictFlaggerAEC.exe
```

### Distribution

The `.exe` file is self-contained and can be shared directly.

---

## Team Workflow

Since you're on Mac and your teammate is on Windows, here's the recommended workflow:

### Option A: Each Builds Their Own Platform (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│                                                              │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │   You (Mac)  │                    │ Teammate (Win)│       │
│  │              │                    │              │       │
│  │ 1. git pull  │                    │ 1. git pull  │       │
│  │ 2. pyinstaller│                   │ 2. pyinstaller│       │
│  │ 3. Flagger.app│                   │ 3. .exe      │       │
│  └──────────────┘                    └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Steps:**

1. **You** push code changes to GitHub
2. **Teammate** pulls latest changes
3. **Each** builds for their own platform
4. **Both** upload executables to GitHub Releases

### Option B: GitHub Actions (Automated)

For automated builds, create `.github/workflows/build.yml`:

```yaml
name: Build Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller pillow tkinterdnd2
      - run: pyinstaller --clean --noconfirm conflict_flagger.spec
      - uses: actions/upload-artifact@v4
        with:
          name: Flagger-macOS
          path: dist/Flagger.app

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller pillow tkinterdnd2
      - run: pyinstaller --clean --noconfirm conflict_flagger.spec
      - uses: actions/upload-artifact@v4
        with:
          name: Flagger-Windows
          path: dist/ConflictFlaggerAEC.exe
```

---

## Phase Configuration

The app supports different analysis phases selected at **runtime** (not build time).

### Available Phases

| Phase | Description | Speed |
|-------|-------------|-------|
| **Comprovació Ràpida** | Codes, units, quantities only | Fast |
| **Anàlisi Completa** | All properties compared | Thorough |

### How Users Select

Users choose the phase via radio buttons in the UI before clicking "Generar Excel".

### Changing Default Phase

To change which phase is selected by default, edit `src/app_comparator.py`:

```python
# Line ~454 - Change default value:
self.selected_phase = tk.StringVar(value=Phase.QUICK_CHECK.value)
# Or:
self.selected_phase = tk.StringVar(value=Phase.FULL_ANALYSIS.value)
```

### Adding New Phases

1. Edit `src/phases/config.py`
2. Add new enum value to `Phase`
3. Create `PhaseConfig` with desired settings
4. Add to `PHASES` dictionary
5. Rebuild the app

Example:
```python
# In src/phases/config.py
class Phase(Enum):
    QUICK_CHECK = "quick_check"
    FULL_ANALYSIS = "full_analysis"
    QUANTITIES_ONLY = "quantities_only"  # NEW

PHASES = {
    # ... existing phases ...
    Phase.QUANTITIES_ONLY: PhaseConfig(
        name="Només Quantitats",
        description="Focus on quantity discrepancies only",
        check_codes=False,
        check_units=False,
        check_quantities=True,
        check_properties=False,
        quantity_tolerance=0.01,  # Stricter
        sheets=["Discrepàncies"],
    ),
}
```

---

## Troubleshooting

### macOS: "App is damaged and can't be opened"

```bash
# Remove quarantine attribute
xattr -cr dist/Flagger.app
```

### macOS: Gatekeeper blocks the app

Right-click > Open > Open anyway, or:
```bash
spctl --add dist/Flagger.app
```

### Windows: Missing DLLs

Install Visual C++ Redistributable:
https://aka.ms/vs/17/release/vc_redist.x64.exe

### Windows: Antivirus blocks the exe

Add an exception for the build directory or sign the executable.

### Import errors at runtime

If you see `ModuleNotFoundError` for phases or other modules:

1. Verify `conflict_flagger.spec` includes all modules in `datas=[]`
2. Clean build: `pyinstaller --clean --noconfirm conflict_flagger.spec`
3. Check `hiddenimports=[]` for any missing dependencies

### Build takes too long

Exclude unnecessary packages in `conflict_flagger.spec`:
```python
excludes=[
    'pytest', 'pytest_cov', 'matplotlib', 'scipy',
    'numpy.testing', 'IPython', 'jupyter',
]
```

---

## Release Checklist

Before creating a release:

- [ ] All tests pass: `python -m pytest`
- [ ] Version updated in `conflict_flagger.spec`
- [ ] Both Mac and Windows builds tested
- [ ] README updated with download links
- [ ] Create GitHub Release with both executables

---

## File Structure Reference

```
conflict-flagger-aec/
├── conflict_flagger.spec     # PyInstaller configuration
├── build_app.py              # Python build helper script
├── build_mac.sh              # macOS build script
├── build_windows.bat         # Windows build script
├── src/
│   ├── app_comparator.py     # Main GUI application
│   ├── phases/
│   │   ├── __init__.py
│   │   └── config.py         # Phase configurations
│   ├── parsers/
│   ├── matching/
│   ├── comparison/
│   └── reporting/
└── dist/                     # Build output (gitignored)
    ├── Flagger.app/          # macOS build
    └── ConflictFlaggerAEC.exe # Windows build
```
