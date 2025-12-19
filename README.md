# IFC-BC3 Conflict Flagger

**A tool to compare BIM models (IFC) with cost estimates (BC3) and flag discrepancies.**

## Purpose

This tool automates the validation of data between:
- **IFC files**: BIM model geometry and properties (from Revit, ArchiCAD, etc.)
- **BC3 files**: Cost estimates in FIEBDC-3 format (from Presto, etc.)

It detects:
- Elements in IFC missing from BC3 (not budgeted)
- Elements in BC3 missing from IFC (orphan budget items)
- Property mismatches between matched elements
- Quantity discrepancies

## Architecture

```
┌─────────────┐     ┌─────────────┐
│   IFC File  │     │  BC3 File   │
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
        │   Matcher    │
        │ Tag ↔ Code   │
        │ GUID ↔ GUID  │
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  Comparator  │
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   Reporter   │
        └──────────────┘
```

## Matching Strategy

Elements are matched using multiple identifiers:

1. **Primary: Tag ↔ Code** - Revit Element ID matches BC3 component code
2. **Secondary: IFC GlobalId ↔ Tipo IfcGUID** - Direct GUID correlation
3. **Fallback: Family + Type name matching**

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m src.main --ifc path/to/model.ifc --bc3 path/to/budget.bc3 --output report.xlsx
```

## Project Structure

```
conflict-flagger/
├── src/
│   ├── parsers/
│   │   ├── ifc_parser.py      # Extract elements from IFC
│   │   └── bc3_parser.py      # Extract elements from BC3
│   ├── matching/
│   │   └── matcher.py         # Link IFC ↔ BC3 elements
│   ├── comparison/
│   │   └── comparator.py      # Find differences
│   ├── reporting/
│   │   └── reporter.py        # Generate output
│   └── main.py
├── tests/
├── data/
│   ├── input/
│   └── output/
├── legacy/                     # Previous implementation
├── requirements.txt
└── README.md
```

## Conflict Types

| Type | Color | Description |
|------|-------|-------------|
| Missing in BC3 | 🟡 Yellow | Element in IFC but not budgeted |
| Missing in IFC | 🟡 Yellow | Budget item without model element |
| Property Mismatch | 🔴 Red | Same element, different values |
| Match OK | 🟢 Green | Element matches in both sources |

## License

MIT
