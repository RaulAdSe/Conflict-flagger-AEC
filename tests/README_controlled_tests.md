# Controlled Test Scenarios for IFC-BC3 Pipeline

This document describes the controlled test scenarios used to verify that the IFC-BC3 comparison pipeline correctly detects expected errors and warnings without introducing false positives.

## Overview

The tests create modified versions of baseline BC3 files with specific, predictable changes and verify that:
1. **Intended errors/warnings are detected** - The pipeline catches the modifications we introduce
2. **Baseline conflicts don't increase** - No false positives are introduced
3. **No baseline conflicts disappear** - Existing valid detections remain intact

## Baseline Data

**Location:** `data/baseline/`
- `GUIA MODELADO V2.ifc` - IFC building model (2.3 MB)
- `GUIA MODELADO V2.bc3` - BC3 budget file (115 KB)

**Baseline Conflict Summary (29 total):**
- 5 Quantity mismatches (pre-existing IFC export issues)
- 1 Code mismatch
- 12 Missing in BC3 (System Panels not budgeted)
- 11 Missing in IFC (orphan budget items)

## Pipeline Properties Checked

| Property | Unit Types | Tolerance | Conflict Type |
|----------|------------|-----------|---------------|
| Total Quantity | Count (u, ud, un) | 0% (exact) | QUANTITY_MISMATCH |
| Total Quantity | Area (m², m2) | 5% | QUANTITY_MISMATCH |
| Total Quantity | Volume (m³, m3) | 5% | QUANTITY_MISMATCH |
| Total Quantity | Length (m, ml) | 2% | QUANTITY_MISMATCH |
| Codes | - | exact match | CODE_MISMATCH |
| Names | - | similarity | NAME_MISMATCH |
| Presence | - | - | MISSING_IN_IFC / MISSING_IN_BC3 |

## Test Scenarios

### Scenario 1: Quantity Mismatches

**Purpose:** Verify the pipeline detects quantity differences that exceed tolerance thresholds.

**Modifications:**
| Element | Type | Unit | Original | Modified | % Change | Expected |
|---------|------|------|----------|----------|----------|----------|
| 350147 | Column | m³ | 63.62 | 75.0 | +17.9% | ERROR (>5% vol) |
| 352900 | Beam | m | 215.1 | 230.0 | +6.9% | ERROR (>2% len) |
| 360466 | Floor | m² | 4922.62 | 5500.0 | +11.7% | ERROR (>5% area) |
| 361849 | Door | u | 2 | 3 | +50% | ERROR (>0% count) |

**Results:**
- ✅ Baseline: 29 conflicts → Scenario: 33 conflicts (+4)
- ✅ All 4 modified elements trigger QUANTITY_MISMATCH errors
- ✅ No unexpected conflicts introduced
- ✅ No baseline conflicts changed

### Scenario 2: Missing Elements

**Purpose:** Verify detection of elements missing from either IFC or BC3.

**Modifications:**
- **Removed from BC3:** 350147 (column), 352900 (beam), 361849 (door)
- **Added orphans (BC3 only):** ORPHAN001 (100 m²), ORPHAN002 (5 u), ORPHAN003 (25 m³)

**Results:**
- ✅ Baseline: 29 conflicts → Scenario: 35 conflicts (+6)
- ✅ 3 MISSING_IN_BC3 warnings for removed elements
- ✅ 3 MISSING_IN_IFC warnings for orphan elements
- ✅ No unexpected conflicts introduced

### Scenario 3: Name/Description Mismatches

**Purpose:** Verify name changes don't break matching or cause false positives.

**Modifications:**
| Element | Original Description | Modified Description |
|---------|----------------------|----------------------|
| 350147 | "Pilar rectangular hormigón - 600 x 600 mm" | "COLUMNA MODIFICADA 60x60" |
| 352900 | "JACENA I - I-220" | "VIGA PERFIL MODIFICADA" |

**Results:**
- ✅ Baseline: 29 conflicts → Scenario: 29 conflicts (unchanged)
- ✅ Elements still matched by code (names don't break matching)
- ✅ No false positives introduced
- ✅ Baseline completely preserved

## Test Files

| File | Purpose |
|------|---------|
| `tests/test_controlled_scenarios.py` | Creates modified BC3 files and runs basic verification |
| `tests/test_regression_scenarios.py` | Comprehensive regression testing against baseline |

## Running the Tests

```bash
# Run controlled scenario tests
PYTHONPATH=. python3 tests/test_controlled_scenarios.py

# Run regression tests (detailed baseline comparison)
PYTHONPATH=. python3 tests/test_regression_scenarios.py

# Run with pytest
PYTHONPATH=. pytest tests/test_controlled_scenarios.py -v
PYTHONPATH=. pytest tests/test_regression_scenarios.py -v
```

## Generated Test Data

Test files are generated in `data/test/`:
- `scenario1_quantity_mismatch.bc3` - Modified quantities
- `scenario2_missing_elements.bc3` - Removed/added elements
- `scenario3_name_mismatch.bc3` - Modified descriptions
- `report_scenario*.xlsx` - Excel reports for visual verification

## Key Implementation Details

### BC3ModifierExtended Class

Extends `BC3Modifier` with additional capabilities:

```python
# Modify quantity in decomposition records
modifier.modify_quantity_in_decomposition("350147", 75.0)

# Remove elements completely (including all references)
modifier.remove_elements_completely(['350147', '352900'])

# Add orphan element with quantity (required for MISSING_IN_IFC detection)
modifier.add_orphan_element_with_quantity('ORPHAN001', 'm2', 'Description', 100.0)
```

### Important Notes

1. **Orphan elements must have quantity > 0** - The comparator skips BC3 elements with zero quantity
2. **Elements matched by code take priority** - Name changes don't affect matching if codes match
3. **Tolerances are unit-dependent** - Count units require exact match, others allow small differences

## Bug Fixes Applied

During test development, a bug was fixed in `src/main.py`:
- Fixed reference to non-existent `summary['property_mismatches']` key
- Fixed `conflict.code` → `conflict.element_code` attribute access
- Added proper import for `ConflictSeverity` enum
