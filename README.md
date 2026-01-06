# Conflict Flagger AEC

**A system for detecting discrepancies between BIM models (IFC) and construction budgets (BC3) for the AEC sector.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Purpose

This tool automates data validation between:
- **IFC files**: Geometry and properties from BIM models (Revit, ArchiCAD, etc.)
- **BC3 files**: Budgets in FIEBDC-3 format (Presto, Arquimedes, TCQ)

### Automatically Detects:

| Type | Description |
|------|-------------|
| Not Budgeted | Elements in IFC that are not in the budget |
| Not Modeled | Budgeted items without an element in the model |
| Value Discrepancies | Different properties between matched elements |
| Quantity Differences | Volumes, areas, or lengths that don't match |

## Installation

```bash
# Clone repository
git clone https://github.com/RaulAdSe/Conflict-flagger-AEC.git
cd Conflict-flagger-AEC

# Install dependencies
pip install -r requirements.txt
```

### Main Dependencies

- `ifcopenshell` - IFC file parser
- `openpyxl` - Excel generation
- `pandas` - Data processing

## Quick Start

### Desktop Application

The easiest way to use Conflict Flagger is the desktop application:

1. Download the executable for your platform:
   - **Windows**: `ConflictFlaggerAEC.exe` (~67 MB)
   - **macOS**: `Flagger.app` (~413 MB)

2. Launch the application and drag & drop your files:
   - Drop `.ifc` file on the left zone
   - Drop `.bc3` file on the right zone

3. Click "Generar Excel" to generate the comparison report

See [Desktop App Documentation](docs/desktop-app.md) for details.

### Command Line

```bash
# Basic comparison
python -m src.main --ifc model.ifc --bc3 budget.bc3

# With options
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    --output report.xlsx \
    --json report.json \
    --tolerance 0.02 \
    -v
```

### Python

```python
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter

# Complete pipeline
ifc_result = IFCParser().parse("model.ifc")
bc3_result = BC3Parser().parse("budget.bc3")
match_result = Matcher().match(ifc_result, bc3_result)
comparison = Comparator().compare(match_result)
Reporter().generate_report(match_result, comparison, "report.xlsx")
```

## Output Report

The system generates Excel reports in **Spanish** with color coding:

### Report Sheets

| Sheet | Content |
|-------|---------|
| **Resumen** | General statistics and project status |
| **Discrepancias** | Detail of all detected conflicts |
| **Elementos Emparejados** | List of correctly linked elements |
| **Sin Presupuestar** | Model elements without budget item |
| **Sin Modelar** | Budgeted items without model element |

### Color Code

| Color | Meaning |
|-------|---------|
| Green | Correct - No issues |
| Yellow | Warning - Review recommended |
| Red | Error - Requires attention |

## Architecture

```
┌─────────────┐     ┌─────────────┐
│  IFC Model  │     │   BC3       │
│   (Revit)   │     │Budget(Presto│
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ IFC Parser  │     │ BC3 Parser  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └────────┬──────────┘
                ▼
        ┌──────────────┐
        │   Matcher    │  ← Matches by GUID, Tag, or Name
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  Comparator  │  ← Detects discrepancies
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   Reporter   │  ← Generates Excel/JSON
        └──────────────┘
```

## Documentation

See the [`docs/`](docs/) folder for detailed documentation:

| Document | Description |
|----------|-------------|
| [Desktop App](docs/desktop-app.md) | Desktop application guide |
| [Guia d'Usuari](docs/guia-usuari.md) | User guide (Catalan) |
| [Architecture](docs/arquitectura.md) | System overview |
| [BC3 Parser](docs/bc3-parser.md) | Budget extraction |
| [IFC Parser](docs/ifc-parser.md) | BIM model extraction |
| [Matcher](docs/matcher.md) | Element matching |
| [Comparator](docs/comparator.md) | Conflict detection |
| [Reporter](docs/reporter.md) | Report generation |
| [CLI](docs/cli.md) | Command line usage |
| [Test Data Generator](docs/test-data-generator.md) | Test data generation |

## Project Structure

```
conflict-flagger-aec/
├── src/
│   ├── parsers/
│   │   ├── ifc_parser.py       # IFC model parser
│   │   └── bc3_parser.py       # BC3 budget parser
│   ├── matching/
│   │   └── matcher.py          # IFC ↔ BC3 matching
│   ├── comparison/
│   │   └── comparator.py       # Discrepancy detection
│   ├── reporting/
│   │   └── reporter.py         # Report generation
│   ├── app_comparator.py       # Desktop application
│   ├── main.py                 # Main CLI
│   └── test_data_generator.py  # Test data generator
├── tests/                      # Unit tests
├── docs/                       # Technical documentation
├── app_design/                 # UI mockups and assets
├── conflict_flagger.spec       # PyInstaller build config
├── data/
│   ├── input/                  # Input files
│   └── output/                 # Generated reports
└── requirements.txt
```

## Testing

```bash
# Run all tests
python -m pytest

# With coverage
python -m pytest --cov=src

# Specific tests
python -m pytest tests/test_comparator.py -v
```

### Generate Test Data

```bash
# Generate test scenarios
python src/test_data_generator.py --mode scenarios
```

This creates 8 scenarios with different types of discrepancies to validate the system.

## Recommended Workflow

1. **Export IFC from Revit** with properties and quantities
2. **Export BC3 from Presto** including IFC GUIDs
3. **Run comparison** with the CLI
4. **Review Excel report** prioritizing errors (red)
5. **Correct discrepancies** in model or budget
6. **Re-run** until complete validation

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

MIT License - See [LICENSE](LICENSE) for details.

## Author

Developed to automate BIM project validation in the AEC sector.
