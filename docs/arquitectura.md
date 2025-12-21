# System Architecture

## Overview

Conflict Flagger AEC is a modular system for detecting discrepancies between BIM models (IFC) and construction budgets (BC3). The system follows a pipeline architecture where each component processes and transforms data.

## Main Components

### 1. Parser Layer

**Responsibility:** Extract structured data from source files.

```
src/parsers/
├── bc3_parser.py   # Extracts budget elements
└── ifc_parser.py   # Extracts BIM model elements
```

- **BC3Parser:** Reads BC3 files (FIEBDC format) and extracts line items with properties
- **IFCParser:** Reads IFC files using ifcopenshell and extracts elements with properties

### 2. Matching Layer

**Responsibility:** Match elements between both data sources.

```
src/matching/
└── matcher.py      # Matches IFC <-> BC3 elements
```

**Matching strategies:**
1. By GUID (IFC GlobalId)
2. By Tag (Revit Element ID)
3. By type name

### 3. Comparison Layer

**Responsibility:** Detect differences between matched elements.

```
src/comparison/
└── comparator.py   # Compares properties and detects conflicts
```

**Conflict types:**
- `PROPERTY_MISMATCH` - Different values
- `MISSING_IN_BC3` - Element only in IFC
- `MISSING_IN_IFC` - Element only in BC3

### 4. Reporting Layer

**Responsibility:** Generate visual reports.

```
src/reporting/
└── reporter.py     # Generates Excel and JSON
```

**Output formats:**
- Excel with color-coded sheets (in Spanish)
- Structured JSON (in Spanish)

## Data Flow

```
                    ┌─────────────────────────────────────────┐
                    │              DATA INPUT                 │
                    └─────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┴───────────────────────────┐
            │                                                       │
            ▼                                                       ▼
    ┌───────────────┐                                       ┌───────────────┐
    │   IFC File    │                                       │   BC3 File    │
    │  (BIM Model)  │                                       │   (Budget)    │
    └───────┬───────┘                                       └───────┬───────┘
            │                                                       │
            ▼                                                       ▼
    ┌───────────────┐                                       ┌───────────────┐
    │   IFCParser   │                                       │   BC3Parser   │
    │               │                                       │               │
    │ - Elements    │                                       │ - Line items  │
    │ - Types       │                                       │ - Properties  │
    │ - Properties  │                                       │ - Hierarchy   │
    └───────┬───────┘                                       └───────┬───────┘
            │                                                       │
            │         ┌─────────────────────────────┐               │
            └────────►│         Matcher             │◄──────────────┘
                      │                             │
                      │ - Match by GUID             │
                      │ - Match by Tag              │
                      │ - Match by Name             │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │        MatchResult          │
                      │                             │
                      │ - matched[]                 │
                      │ - ifc_only[]                │
                      │ - bc3_only[]                │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │        Comparator           │
                      │                             │
                      │ - Compare properties        │
                      │ - Detect discrepancies      │
                      │ - Classify severity         │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │     ComparisonResult        │
                      │                             │
                      │ - conflicts[]               │
                      │ - summary stats             │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │         Reporter            │
                      │                             │
                      │ - Color-coded Excel         │
                      │ - Structured JSON           │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │              DATA OUTPUT                │
                    │                                         │
                    │  ┌─────────────┐    ┌─────────────┐    │
                    │  │   Excel     │    │    JSON     │    │
                    │  │  (.xlsx)    │    │   (.json)   │    │
                    │  └─────────────┘    └─────────────┘    │
                    └─────────────────────────────────────────┘
```

## Data Models

### BC3Element

```python
@dataclass
class BC3Element:
    code: str              # Unique code (e.g., "350147")
    unit: str              # Unit of measure
    description: str       # Description
    price: float           # Unit price
    family_name: str       # Family (e.g., "Column")
    type_name: str         # Type (e.g., "600x600")
    properties: dict       # Extended properties
    ifc_guid: str          # IFC GUID if available
```

### IFCElement

```python
@dataclass
class IFCElement:
    global_id: str         # IFC GUID (22 chars)
    tag: str               # Revit ID
    name: str              # Full name
    ifc_class: str         # IFC class (e.g., "IfcColumn")
    type_id: str           # Type GUID
    type_name: str         # Type name
    properties: dict       # Extracted properties
    quantities: dict       # Quantities (area, volume, etc.)
```

### MatchedPair

```python
@dataclass
class MatchedPair:
    status: MatchStatus    # MATCHED, IFC_ONLY, BC3_ONLY
    method: MatchMethod    # GUID, TAG, NAME
    ifc_type: IFCType      # IFC element
    bc3_element: BC3Element # BC3 element
    confidence: float      # Confidence level (0-1)
```

### Conflict

```python
@dataclass
class Conflict:
    conflict_type: ConflictType  # Conflict type
    severity: Severity           # ERROR, WARNING, INFO
    code: str                    # Element code
    element_name: str            # Element name
    property_name: str           # Affected property
    ifc_value: Any              # Value in IFC
    bc3_value: Any              # Value in BC3
    message: str                 # Descriptive message
```

## Design Patterns

### 1. Pipeline Pattern
Each component processes data and passes it to the next in the chain.

### 2. Strategy Pattern
The Matcher uses different matching strategies (GUID, Tag, Name).

### 3. Builder Pattern
The Reporter builds the Excel report sheet by sheet.

### 4. Dataclass Pattern
All data models use dataclasses for immutability and clarity.

## Extensibility

### Adding a new parser
1. Create class in `src/parsers/`
2. Implement `parse()` method returning compatible structure

### Adding a new matching strategy
1. Add new value to `MatchMethod` enum
2. Implement logic in `Matcher._match_by_*()`

### Adding a new report type
1. Extend `Reporter` class
2. Implement `generate_*_report()` method

## Configuration

### ReportConfig

```python
@dataclass
class ReportConfig:
    color_error: str = "FF6B6B"    # Color for errors
    color_warning: str = "FFE66D"  # Color for warnings
    color_ok: str = "7ED957"       # Color for OK
    max_rows: int = 10000          # Maximum rows
```

### Numeric Tolerance

```python
comparator = Comparator(tolerance=0.01)  # 1% tolerance
```

## Performance

- Large IFC files (>100MB) may take several seconds to parse
- Matching is O(n*m) worst case, but optimized with indexes
- Excel report is generated in memory before writing to disk
