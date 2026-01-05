# Desktop Application

## Overview

Conflict Flagger AEC includes a cross-platform desktop application with a modern, user-friendly interface. The app provides drag-and-drop functionality for file selection and generates comprehensive Excel reports comparing BIM models (IFC) with construction budgets (BC3).

## Features

- **Modern UI**: Clean interface matching macOS design guidelines
- **Drag & Drop**: Drop IFC and BC3 files directly onto upload zones
- **Cross-platform**: Native builds for Windows (.exe) and macOS
- **Integrated Backend**: Uses the full parsing, matching, and comparison pipeline
- **Catalan Interface**: All UI text in Catalan for local use
- **Automatic Report Location**: Reports saved to Downloads folder by default

## Installation

### Pre-built Executables

Download the appropriate executable for your platform:

| Platform | File | Size |
|----------|------|------|
| Windows | `ConflictFlaggerAEC.exe` | ~67 MB |
| macOS | `Flagger` | ~134 MB |

### From Source

```bash
# Install dependencies
pip install -r requirements.txt
pip install tkinterdnd2 pillow

# Run the application
python src/app_comparator.py
```

## Usage

1. **Launch the Application**
   - Windows: Double-click `ConflictFlaggerAEC.exe`
   - macOS: Double-click `Flagger`

2. **Select Files**
   - Drag and drop your `.ifc` file onto the left upload zone
   - Drag and drop your `.bc3` file onto the right upload zone
   - Or click on each zone to browse and select files

3. **Generate Report**
   - Click the green "Generar Excel" button
   - Wait for processing to complete
   - The Excel report opens automatically

4. **Review Results**
   - Report is saved in your Downloads folder
   - Filename format: `informe_YYYYMMDD_HHMMSS.xlsx`

## Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  [Servitec Logo]                                     Flagger    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Compara fitxers IFC i BC3 per detectar discrepàncies         │
│                                                                 │
│  ┌─────────────────────────┐   ┌─────────────────────────┐     │
│  │      📄 .IFC            │   │      📄 .BC3            │     │
│  │                         │   │                         │     │
│  │   Arrossega aquí o      │   │   Arrossega aquí o      │     │
│  │   fes clic per pujar    │   │   fes clic per pujar    │     │
│  │                         │   │                         │     │
│  │   Model BIM             │   │   Pressupost            │     │
│  └─────────────────────────┘   └─────────────────────────┘     │
│                                                                 │
│              ┌────────────────────────────┐                    │
│              │     Generar Excel          │                    │
│              └────────────────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Building from Source

### Requirements

- Python 3.10+
- PyInstaller
- All project dependencies

### Build Commands

**macOS:**
```bash
pyinstaller --clean --noconfirm conflict_flagger.spec
# Output: dist/Flagger
```

**Windows (native):**
```bash
pyinstaller --clean --noconfirm conflict_flagger.spec
# Output: dist/ConflictFlaggerAEC.exe
```

**Windows (via Wine on macOS):**
```bash
# Ensure Wine has Python with all dependencies installed
wine python -m pip install ifcopenshell tkinterdnd2 pillow openpyxl pyinstaller

# Build
wine python -m PyInstaller --clean --noconfirm --distpath dist_win conflict_flagger.spec
# Output: dist_win/ConflictFlaggerAEC.exe
```

## Technical Details

### Architecture

The desktop app integrates with the core library modules:

```
app_comparator.py
    ├── src/parsers/ifc_parser.py    # IFC file parsing
    ├── src/parsers/bc3_parser.py    # BC3 file parsing
    ├── src/matching/matcher.py       # Element matching
    ├── src/comparison/comparator.py  # Discrepancy detection
    └── src/reporting/reporter.py     # Excel report generation
```

### Dependencies

| Library | Purpose |
|---------|---------|
| `tkinter` | Base GUI framework |
| `tkinterdnd2` | Drag and drop support |
| `PIL/Pillow` | Logo image display |
| `ifcopenshell` | IFC file parsing |
| `openpyxl` | Excel report generation |

### PyInstaller Spec

The `conflict_flagger.spec` file configures:
- Single-file executable (compressed)
- All hidden imports for ifcopenshell
- Data files (parsers, logo, etc.)
- Platform-specific settings (argv_emulation for macOS)

## Output Report

The generated Excel report includes:

| Sheet | Description |
|-------|-------------|
| Resum | Summary statistics |
| Discrepàncies | Detected conflicts with details |
| Elements Emparellats | Successfully matched elements |
| Sense Pressupostar | IFC elements without budget match |
| Sense Modelar | Budget items without IFC element |
| Resum Elements | Consolidated element summary |

## Troubleshooting

### App doesn't start

- **Windows**: Ensure Visual C++ Redistributable is installed
- **macOS**: Right-click and select "Open" to bypass Gatekeeper

### Drag and drop not working

- Ensure `tkinterdnd2` is installed
- On some systems, click-to-browse is the fallback

### Missing ifcopenshell error

- The pre-built executables include all dependencies
- If building from source, install with: `pip install ifcopenshell`

### Report not opening

- Check your Downloads folder
- Ensure you have an application to open .xlsx files
