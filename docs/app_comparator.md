# Technical Documentation: Desktop Application (app_comparator.py)

## 1. Introduction

The desktop application is a modern Tkinter-based GUI that provides a user-friendly interface for comparing BIM models (IFC) with construction budgets (BC3). It features drag-and-drop file selection, a clean macOS-inspired design, and generates comprehensive Excel reports.

## 2. Dependencies

| Library | Purpose |
|---------|---------|
| `tkinter` | Base GUI framework (Python standard library) |
| `tkinterdnd2` | Drag and drop file support |
| `PIL/Pillow` | Logo image display |
| `ifcopenshell` | IFC file parsing |
| `openpyxl` | Excel report generation |

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     app_comparator.py                         │
├──────────────────────────────────────────────────────────────┤
│  ConflictFlaggerApp (Main Application)                       │
│    ├── ModernUploadZone (Custom widget for file upload)      │
│    ├── ModernButton (Custom styled button)                   │
│    └── Processing Pipeline                                   │
│          ├── IFCParser                                       │
│          ├── BC3Parser                                       │
│          ├── Matcher                                         │
│          ├── Comparator                                      │
│          └── Reporter                                        │
└──────────────────────────────────────────────────────────────┘
```

## 4. Key Components

### 4.1 ModernUploadZone

A custom Canvas widget that provides:
- Visual states: empty, uploaded, drag-over
- Dashed border animation for empty state
- Solid green border for uploaded state
- Blue highlight during drag-over
- File type validation (.ifc or .bc3)
- Filename display after upload

```python
class ModernUploadZone(tk.Canvas):
    def __init__(self, parent, file_type, hint, on_click, on_drop=None):
        # Colors matching macOS design
        self.bg_empty = "#FAFAFA"
        self.bg_uploaded = "#F0FFF4"
        self.border_uploaded = "#34C759"
        # ...
```

### 4.2 ModernButton

A custom Canvas widget that renders:
- Rounded rectangle background
- Gradient-like appearance
- Hover and press states
- Custom colors and fonts

### 4.3 ConflictFlaggerApp

Main application class that:
- Creates the window with proper sizing
- Displays the Servitec logo
- Manages file selection state
- Coordinates the comparison pipeline
- Handles report generation and display

## 5. Processing Pipeline

When the user clicks "Generar Excel", the app:

1. **Parses IFC** - Extracts elements, properties, and quantities
2. **Parses BC3** - Extracts budget items and codes
3. **Matches elements** - Links IFC elements to BC3 items by GUID/Tag/Name
4. **Compares properties** - Detects discrepancies in matched pairs
5. **Generates report** - Creates Excel with multiple sheets

```python
def _generate_report(self):
    ifc_result = IFCParser().parse(self.ifc_file)
    bc3_result = BC3Parser().parse(self.bc3_file)
    matcher = Matcher(match_by_name=True)
    match_result = matcher.match(ifc_result, bc3_result)
    comparator = Comparator(tolerance=0.01)
    comparison = comparator.compare(match_result)
    reporter = Reporter()
    reporter.generate_report(match_result, comparison, output_path)
```

## 6. User Interface (Catalan)

The interface uses Catalan text:

| Element | Text |
|---------|------|
| Title | "Flagger" |
| Subtitle | "Compara fitxers IFC i BC3 per detectar discrepàncies" |
| Upload hint | "Arrossega aquí o fes clic per pujar" |
| IFC label | "Model BIM" |
| BC3 label | "Pressupost" |
| Button | "Generar Excel" |
| Success dialog | "Informe Generat" |

## 7. Output Location

Reports are saved to the Downloads folder by default:

```python
def _get_output_directory(self):
    downloads = Path.home() / "Downloads"
    if downloads.exists() and os.access(str(downloads), os.W_OK):
        return downloads
    # Fallbacks: Desktop, Home, Current directory
```

Filename format: `informe_YYYYMMDD_HHMMSS.xlsx`

## 8. Drag and Drop Support

Uses `tkinterdnd2` for native drag-and-drop:

```python
if HAS_DND:
    self.drop_target_register(DND_FILES)
    self.dnd_bind('<<DropEnter>>', self._on_drag_enter)
    self.dnd_bind('<<DropLeave>>', self._on_drag_leave)
    self.dnd_bind('<<Drop>>', self._on_drop)
```

Falls back to click-to-browse if tkinterdnd2 is not available.

## 9. Logo Display

The Servitec logo is displayed in the upper-right corner:

```python
def _load_logo(self):
    logo_path = self._get_logo_path()
    if logo_path and HAS_PIL:
        img = Image.open(str(logo_path))
        # Resize maintaining aspect ratio
        target_height = 25
        aspect = img.width / img.height
        new_width = int(target_height * aspect)
        img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        self.logo_image = ImageTk.PhotoImage(img)
```

## 10. Build Configuration

The `conflict_flagger.spec` file configures PyInstaller:

- **Single-file mode**: Creates one compressed executable
- **Hidden imports**: Includes ifcopenshell submodules
- **Data files**: Bundles parsers, matching, comparison, reporting modules
- **Platform naming**: "Flagger" on macOS, "ConflictFlaggerAEC" on Windows

## 11. Running the Application

### Development
```bash
python src/app_comparator.py
```

### Built executable
```bash
# macOS
./dist/Flagger

# Windows
dist_win\ConflictFlaggerAEC.exe
```

## 12. Error Handling

The app shows user-friendly error dialogs:

- File validation errors (wrong extension)
- Parsing errors (invalid IFC/BC3)
- Write permission errors
- General exceptions with traceback
