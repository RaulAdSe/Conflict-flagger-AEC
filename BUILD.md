# Build Guide - Conflict Flagger AEC

## TL;DR - Quick Start on Mac

```bash
# First time setup (creates both venvs)
./setup_dev.sh

# Run tests
source venv/bin/activate && pytest tests/

# Build Windows .exe
wine venv_win/Scripts/pyinstaller.exe --clean --noconfirm conflict_flagger.spec
```

---

## Understanding the Two Virtual Environments

**On Mac, you need TWO separate Python environments:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR MAC                                         │
│                                                                          │
│   ┌─────────────────────┐         ┌─────────────────────────────────┐   │
│   │      venv/          │         │         venv_win/               │   │
│   │   (Mac Python)      │         │     (Wine = Windows Python)     │   │
│   │                     │         │                                 │   │
│   │  • Run tests        │         │  • Build .exe for Windows       │   │
│   │  • Development      │         │  • Uses Python inside Wine      │   │
│   │  • Build .app       │         │  • Like having a Windows PC     │   │
│   │                     │         │                                 │   │
│   │  Activate:          │         │  Use with:                      │   │
│   │  source venv/bin/   │         │  wine venv_win/Scripts/...      │   │
│   │         activate    │         │                                 │   │
│   └─────────────────────┘         └─────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why?**
- `venv/` = Regular Mac Python. For developing, testing, and building the Mac `.app`
- `venv_win/` = Python running inside Wine (a Windows emulator). This lets you build a **real Windows .exe** without needing a Windows computer!

---

## Output Summary

| Platform | Output | Who Can Build |
|----------|--------|---------------|
| Windows | `ConflictFlaggerAEC.exe` (~67 MB) | Both (native or via Wine) |
| macOS | `Flagger.app` (~413 MB) | Mac only (optional) |

---

## Building on Windows (Native)

### Prerequisites

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/)
   - **Important**: Check "Add Python to PATH" during installation

2. Clone and setup:
```powershell
git clone https://github.com/RaulAdSe/Conflict-flagger-AEC.git
cd Conflict-flagger-AEC

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller pillow tkinterdnd2
```

### Build the .exe

```powershell
pyinstaller --clean --noconfirm conflict_flagger.spec
```

Or use the batch file:
```powershell
.\build_windows.bat
```

### Output

```
dist\
└── ConflictFlaggerAEC.exe    # Ready to distribute!
```

---

## Building on macOS via Wine

### Prerequisites

1. Install Wine (if not already installed):
```bash
# Using Homebrew
brew install --cask wine-stable

# Or using MacPorts
sudo port install wine
```

2. Install Python **inside Wine**:
```bash
# Download Python installer
curl -O https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe

# Run installer in Wine
wine python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

3. Setup the project in Wine:
```bash
cd Conflict-flagger-AEC

# Create venv using Wine's Python
wine python -m venv venv_win

# Activate and install dependencies
wine venv_win/Scripts/pip.exe install -r requirements.txt
wine venv_win/Scripts/pip.exe install pyinstaller pillow tkinterdnd2
```

### Build the .exe

```bash
wine venv_win/Scripts/pyinstaller.exe --clean --noconfirm conflict_flagger.spec
```

Or shorter (if Wine Python is in PATH):
```bash
wine python -m PyInstaller --clean --noconfirm --distpath dist_win conflict_flagger.spec
```

### Output

```
dist_win/
└── ConflictFlaggerAEC.exe    # Windows executable built on Mac!
```

### Testing with Wine

```bash
wine dist_win/ConflictFlaggerAEC.exe
```

---

## Building macOS .app (Optional)

If you also want a native Mac app:

```bash
# Activate Mac venv (not Wine)
source venv/bin/activate

# Build
pyinstaller --clean --noconfirm conflict_flagger.spec
```

Output: `dist/Flagger.app/`

---

## Team Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│                      GitHub Repository                           │
│                                                                   │
│   ┌─────────────────────┐          ┌─────────────────────┐       │
│   │     You (Mac)       │          │   Teammate (Win)    │       │
│   │                     │          │                     │       │
│   │  1. git pull        │          │  1. git pull        │       │
│   │  2. wine pyinstaller│          │  2. pyinstaller     │       │
│   │  3. .exe ✓          │          │  3. .exe ✓          │       │
│   │                     │          │                     │       │
│   │  (optional: .app)   │          │                     │       │
│   └─────────────────────┘          └─────────────────────┘       │
│                                                                   │
│   Either of you can produce the Windows .exe for distribution    │
└──────────────────────────────────────────────────────────────────┘
```

**Advantages of this setup:**
- No dependency on one person for builds
- Either can release when needed
- Wine builds are identical to native Windows builds

---

## Quick Reference

### For your teammate (Windows):
```powershell
git pull
venv\Scripts\activate
pyinstaller --clean --noconfirm conflict_flagger.spec
# Output: dist\ConflictFlaggerAEC.exe
```

### For you (Mac via Wine):
```bash
git pull
wine venv_win/Scripts/pyinstaller.exe --clean --noconfirm conflict_flagger.spec
# Output: dist/ConflictFlaggerAEC.exe
```

---

## Phase Configuration

The app supports different analysis phases selected at **runtime** (not build time).

| Phase | Description | Speed |
|-------|-------------|-------|
| **Comprovació Ràpida** | Codes, units, quantities only | Fast |
| **Anàlisi Completa** | All properties compared | Thorough |

Users choose the phase via radio buttons in the UI before clicking "Generar Excel".

### Changing Default Phase

Edit `src/app_comparator.py`:
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

### Wine: Python not found

```bash
# Check Wine Python installation
wine python --version

# If not found, reinstall:
wine python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

### Wine: Missing DLLs

```bash
# Install Visual C++ runtime in Wine
winetricks vcrun2019
```

### Wine: `ucrtbase.dll.crealf` error

If you see `wine: Unimplemented function ucrtbase.dll.crealf`, downgrade numpy:
```bash
wine venv_win/Scripts/pip.exe install "numpy<2.0" --force-reinstall
```

Wine 10.0 doesn't support numpy 2.x's use of `crealf()`. Use numpy 1.26.x instead.

### Wine: Build hangs or crashes

Try with a fresh Wine prefix:
```bash
WINEPREFIX=~/.wine_flagger wine python -m venv venv_win
# ... continue with setup
```

### Windows: Antivirus blocks the exe

Add an exception for the build directory or sign the executable.

### Import errors at runtime

If you see `ModuleNotFoundError` for phases or other modules:

1. Verify `conflict_flagger.spec` includes all modules in `datas=[]`
2. Clean build with `--clean` flag
3. Delete `build/` and `dist/` folders and rebuild

---

## Release Checklist

Before creating a release:

- [ ] All tests pass: `python -m pytest`
- [ ] Version updated in `conflict_flagger.spec` (if needed)
- [ ] Windows .exe tested (native or Wine)
- [ ] Create GitHub Release with the executable

---

## File Structure

```
conflict-flagger-aec/
├── conflict_flagger.spec     # PyInstaller configuration
├── build_app.py              # Python build helper
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
├── venv/                     # Mac Python venv
├── venv_win/                 # Wine Python venv (Mac only)
└── dist/                     # Build output
    └── ConflictFlaggerAEC.exe
```
