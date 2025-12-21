# Conflict Flagger AEC - Technical Documentation

A system for detecting discrepancies between BIM models (IFC) and cost estimates (BC3) for the AEC (Architecture, Engineering, Construction) sector.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture](arquitectura.md) | System overview and data flow |
| [BC3 Parser](bc3-parser.md) | Extracting data from BC3 budget files |
| [IFC Parser](ifc-parser.md) | Extracting data from BIM models (IFC format) |
| [Matcher](matcher.md) | Element matching between IFC and BC3 |
| [Comparator](comparator.md) | Discrepancy and conflict detection |
| [Reporter](reporter.md) | Excel and JSON report generation |
| [CLI](cli.md) | Command line interface |
| [Test Data Generator](test-data-generator.md) | Test data generation tools |
| [Desktop App](desktop-app.md) | Future plans for desktop application |

## System Requirements

- Python 3.10+
- ifcopenshell
- openpyxl
- pandas

## Quick Start

```bash
pip install -r requirements.txt
python -m src.main --ifc model.ifc --bc3 budget.bc3 --output report.xlsx
```

## Project Structure

```
src/
├── parsers/
│   ├── bc3_parser.py    # BC3 file parser
│   └── ifc_parser.py    # IFC file parser
├── matching/
│   └── matcher.py       # Element matching
├── comparison/
│   └── comparator.py    # Conflict detection
├── reporting/
│   └── reporter.py      # Report generation
├── main.py              # Main CLI
└── test_data_generator.py  # Test data generator
```

## Data Flow

```
┌─────────┐     ┌─────────┐
│  IFC    │     │  BC3    │
│  File   │     │  File   │
└────┬────┘     └────┬────┘
     │               │
     ▼               ▼
┌─────────┐     ┌─────────┐
│  IFC    │     │  BC3    │
│ Parser  │     │ Parser  │
└────┬────┘     └────┬────┘
     │               │
     └───────┬───────┘
             │
             ▼
       ┌───────────┐
       │  Matcher  │
       └─────┬─────┘
             │
             ▼
       ┌───────────┐
       │Comparator │
       └─────┬─────┘
             │
             ▼
       ┌───────────┐
       │ Reporter  │
       └─────┬─────┘
             │
             ▼
    ┌─────────────────┐
    │ Excel / JSON    │
    │    Report       │
    └─────────────────┘
```

## Output Language

**Note:** While this documentation is in English, the generated reports (Excel/JSON) are in **Spanish** for end-users in the Spanish AEC market.

## License

Private project - All rights reserved.
