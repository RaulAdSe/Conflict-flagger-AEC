# Comparator

## Description

The Comparator analyzes matched elements and detects discrepancies between values in the IFC model and BC3 budget. It generates a list of conflicts classified by type and severity.

## Location

```
src/comparison/comparator.py
```

## Main Classes

### ConflictType (Enum)

```python
class ConflictType(Enum):
    PROPERTY_MISMATCH = "property_mismatch"  # Different value
    MISSING_IN_BC3 = "missing_in_bc3"        # Missing in budget
    MISSING_IN_IFC = "missing_in_ifc"        # Missing in model
    QUANTITY_MISMATCH = "quantity_mismatch"  # Different quantity
    TYPE_MISMATCH = "type_mismatch"          # Different type
```

### ConflictSeverity (Enum)

```python
class ConflictSeverity(Enum):
    ERROR = "error"       # Requires immediate action
    WARNING = "warning"   # Review recommended
    INFO = "info"         # Informational
```

### Conflict

```python
@dataclass
class Conflict:
    conflict_type: ConflictType    # Conflict type
    severity: ConflictSeverity     # Severity level
    code: str                      # Element code
    element_name: str              # Element name
    property_name: Optional[str]   # Affected property
    ifc_value: Any                 # Value in IFC
    bc3_value: Any                 # Value in BC3
    message: str                   # Conflict description
```

### ComparisonResult

```python
@dataclass
class ComparisonResult:
    conflicts: list[Conflict]      # List of conflicts
    missing_in_bc3: int            # Unbudgeted elements
    missing_in_ifc: int            # Unmodeled items
    property_mismatches: int       # Value discrepancies
    total_matched: int             # Total compared
    total_with_conflicts: int      # With at least 1 conflict

    def summary(self) -> dict:
        """Results summary."""
        return {
            "total_conflicts": len(self.conflicts),
            "errors": len(self.get_by_severity(ConflictSeverity.ERROR)),
            "warnings": len(self.get_by_severity(ConflictSeverity.WARNING)),
            "property_mismatches": self.property_mismatches,
            "missing_in_bc3": self.missing_in_bc3,
            "missing_in_ifc": self.missing_in_ifc
        }
```

## Basic Usage

```python
from src.comparison.comparator import Comparator

# Create comparator
comparator = Comparator(tolerance=0.01)  # 1% tolerance

# Compare
result = comparator.compare(match_result)

# Analyze results
print(f"Total conflicts: {len(result.conflicts)}")
print(f"Errors: {result.summary()['errors']}")
print(f"Warnings: {result.summary()['warnings']}")
```

## Comparison Types

### 1. Dimensional Properties

Compares dimensions like height, width, length:

```python
# IFC: h = 0.6 (meters)
# BC3: h = 0.6 (meters)
# → No conflict

# IFC: h = 0.6
# BC3: h = 0.8
# → PROPERTY_MISMATCH (ERROR)
```

**Properties compared:**
- `h` - Height
- `b` - Width/Base
- `L` - Length
- `e` - Thickness

### 2. Quantities

Compares volumes, areas, etc:

```python
# IFC: Volume = 2.16 m³
# BC3: Quantity = 2.20 m³
# Difference = 1.8% → Within tolerance

# IFC: Volume = 2.16 m³
# BC3: Quantity = 3.00 m³
# Difference = 38.9% → QUANTITY_MISMATCH
```

### 3. Missing Elements

```python
# Element in IFC but not in BC3
→ MISSING_IN_BC3 (WARNING)

# Element in BC3 but not in IFC
→ MISSING_IN_IFC (WARNING)
```

## Configuration

### Numeric Tolerance

```python
# 1% tolerance (default)
comparator = Comparator(tolerance=0.01)

# 5% tolerance (more permissive)
comparator = Comparator(tolerance=0.05)

# No tolerance (exact)
comparator = Comparator(tolerance=0.0)
```

### String Comparison

```python
# Default: case-insensitive
# "Column" == "COLUMN" → True

# Ignore extra spaces
# "Column  600x600" == "Column 600x600" → True
```

## Conflict Analysis

### By Type

```python
# Get only property discrepancies
property_conflicts = result.get_by_type(ConflictType.PROPERTY_MISMATCH)

for conflict in property_conflicts:
    print(f"{conflict.code}: {conflict.property_name}")
    print(f"  IFC: {conflict.ifc_value}")
    print(f"  BC3: {conflict.bc3_value}")
```

### By Severity

```python
# Critical errors only
errors = result.get_by_severity(ConflictSeverity.ERROR)

# Warnings only
warnings = result.get_by_severity(ConflictSeverity.WARNING)
```

### By Element

```python
# Conflicts for a specific element
code = "350147"
element_conflicts = [c for c in result.conflicts if c.code == code]
```

## Conflict Severity

| Type | Severity | Description |
|------|----------|-------------|
| `PROPERTY_MISMATCH` | ERROR | Different property values |
| `QUANTITY_MISMATCH` | ERROR | Quantities don't match |
| `TYPE_MISMATCH` | ERROR | Different types |
| `MISSING_IN_BC3` | WARNING | Unbudgeted element |
| `MISSING_IN_IFC` | WARNING | Unmodeled item |

## Complete Example

```python
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator

# Parse
ifc_result = IFCParser().parse("model.ifc")
bc3_result = BC3Parser().parse("budget.bc3")

# Match
match_result = Matcher().match(ifc_result, bc3_result)

# Compare with 2% tolerance
comparator = Comparator(tolerance=0.02)
comparison = comparator.compare(match_result)

# Show summary
summary = comparison.summary()
print(f"""
COMPARISON SUMMARY
==================
Total conflicts: {summary['total_conflicts']}
  - Errors: {summary['errors']}
  - Warnings: {summary['warnings']}

Details:
  - Value discrepancies: {summary['property_mismatches']}
  - Not budgeted: {summary['missing_in_bc3']}
  - Not modeled: {summary['missing_in_ifc']}
""")

# List errors
if summary['errors'] > 0:
    print("\nERRORS DETECTED:")
    for conflict in comparison.get_by_severity(ConflictSeverity.ERROR):
        print(f"  [{conflict.code}] {conflict.message}")
        if conflict.property_name:
            print(f"    {conflict.property_name}: {conflict.ifc_value} vs {conflict.bc3_value}")
```

## Best Practices

### 1. Adjust Tolerance

```python
# Structural elements: low tolerance
structural_comparator = Comparator(tolerance=0.01)

# Finishes: higher tolerance
finishes_comparator = Comparator(tolerance=0.05)
```

### 2. Filter Relevant Conflicts

```python
# Ignore INFO in report
relevant = [c for c in result.conflicts
            if c.severity != ConflictSeverity.INFO]
```

### 3. Prioritize by Severity

```python
# Sort: errors first
sorted_conflicts = sorted(
    result.conflicts,
    key=lambda c: (c.severity != ConflictSeverity.ERROR,
                   c.severity != ConflictSeverity.WARNING)
)
```

## Troubleshooting

### Many False Positives

**Cause:** Tolerance too low
```python
# Increase tolerance
comparator = Comparator(tolerance=0.05)
```

### Different Units

**Cause:** IFC in meters, BC3 in centimeters
```python
# Normalize before comparing
# (implement unit conversion)
```

### Properties Not Found

**Cause:** Different names in IFC vs BC3
```python
# Check property names
print("IFC properties:", ifc_element.properties.keys())
print("BC3 properties:", bc3_element.properties.keys())
```
