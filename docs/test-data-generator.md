# Test Data Generator

## Description

Tool for generating variants of BC3 and IFC files with controlled modifications. Useful for testing and demonstrations of the system.

## Location

```
src/test_data_generator.py
```

## Main Classes

### BC3Modifier

Modifies BC3 files to create test scenarios.

```python
from src.test_data_generator import BC3Modifier

modifier = BC3Modifier("budget.bc3")
modifier.remove_elements(['350147', '350148'])
modifier.modify_property('350149', 'h', '0.8')
modifier.add_orphan_element('NEW001', 'm2', 'New item', 100.0)
modifier.save("budget_modified.bc3")
```

#### Methods

| Method | Description |
|--------|-------------|
| `remove_elements(codes)` | Remove elements by code |
| `modify_property(code, prop, value)` | Modify element property |
| `add_orphan_element(...)` | Add orphan element |
| `change_description(code, desc)` | Change description |
| `save(path)` | Save modified file |

### IFCModifier

Modifies IFC files using ifcopenshell.

```python
from src.test_data_generator import IFCModifier

modifier = IFCModifier("model.ifc")
modifier.remove_elements_by_class('IfcColumn', count=3)
modifier.add_dummy_element('IfcBuildingElementProxy', 'New', 'TAG001')
modifier.save("model_modified.ifc")
```

#### Methods

| Method | Description |
|--------|-------------|
| `remove_elements_by_tags(tags)` | Remove elements by tag |
| `remove_elements_by_class(class, count)` | Remove N elements of a class |
| `modify_element_name(tag, name)` | Change element name |
| `add_dummy_element(...)` | Add dummy element |
| `save(path)` | Save modified file |

## CLI Usage

### Generate Complete Scenarios

```bash
python src/test_data_generator.py --mode scenarios
```

Generates 8 test scenarios with modified BC3/IFC pairs.

### BC3 Variants Only

```bash
python src/test_data_generator.py --mode bc3
```

### IFC Variants Only

```bash
python src/test_data_generator.py --mode ifc
```

### All

```bash
python src/test_data_generator.py --mode all
```

### Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--bc3` | `data/input/...bc3` | Source BC3 file |
| `--ifc` | `data/input/...ifc` | Source IFC file |
| `--output-dir`, `-o` | `data/test_variants` | Output directory |
| `--mode` | `scenarios` | Mode: bc3, ifc, scenarios, all |

## Generated Scenarios

### 1. Baseline

- BC3: No modifications
- IFC: No modifications
- Purpose: Verify no false positives

### 2. BC3 Missing

- BC3: 4 elements removed
- IFC: No modifications
- Purpose: Detect unbudgeted elements

### 3. IFC Missing

- BC3: No modifications
- IFC: 4 columns removed
- Purpose: Detect unmodeled items

### 4. Property Mismatch

- BC3: Properties h, b modified
- IFC: No modifications
- Purpose: Detect value discrepancies

### 5. BC3 Orphans

- BC3: 3 orphan items added
- IFC: No modifications
- Purpose: Detect items without model

### 6. IFC Orphans

- BC3: No modifications
- IFC: 2 dummy elements added
- Purpose: Detect elements without budget

### 7. Combined

- BC3: 2 removed, 1 modified, 1 added
- IFC: 2 removed, 1 added
- Purpose: Realistic mixed scenario

### 8. Stress Test

- BC3: 8 elements removed
- IFC: 10 elements removed
- Purpose: Performance testing

## Output Structure

```
data/test_variants/
├── bc3_variants/
│   ├── bc3_elements_removed.bc3
│   ├── bc3_properties_modified.bc3
│   ├── bc3_orphan_elements.bc3
│   ├── bc3_combined_issues.bc3
│   └── bc3_identical.bc3
├── ifc_variants/
│   ├── ifc_columns_removed.ifc
│   ├── ifc_beams_removed.ifc
│   ├── ifc_orphan_elements.ifc
│   ├── ifc_combined_issues.ifc
│   └── ifc_identical.ifc
└── scenarios/
    ├── scenario_baseline.bc3
    ├── scenario_baseline.ifc
    ├── scenario_bc3_missing.bc3
    ├── scenario_bc3_missing.ifc
    └── ...
```

## Programmatic Usage

### Create Custom Variants

```python
from src.test_data_generator import BC3Modifier, IFCModifier

# Create BC3 with specific elements removed
bc3_mod = BC3Modifier("budget.bc3")
bc3_mod.remove_elements(['350147', '350148', '350149'])
bc3_mod.save("test_missing_columns.bc3")

# Create IFC with columns removed
ifc_mod = IFCModifier("model.ifc")
ifc_mod.remove_elements_by_class('IfcColumn', count=5)
ifc_mod.save("test_missing_columns.ifc")
```

### Generate Scenarios Programmatically

```python
from src.test_data_generator import create_test_scenarios

scenarios = create_test_scenarios(
    source_bc3="budget.bc3",
    source_ifc="model.ifc",
    output_dir="my_scenarios/"
)

for name, info in scenarios.items():
    print(f"{name}:")
    print(f"  BC3: {info['bc3']}")
    print(f"  IFC: {info['ifc']}")
    print(f"  Description: {info['description']}")
```

## Validate Scenarios

Run comparison on each scenario:

```bash
for scenario in baseline bc3_missing ifc_missing property_mismatch; do
    echo "=== $scenario ==="
    python -m src.main \
        --ifc "data/test_variants/scenarios/scenario_${scenario}.ifc" \
        --bc3 "data/test_variants/scenarios/scenario_${scenario}.bc3" \
        --output "reports/report_${scenario}.xlsx"
done
```

## Use Cases

### 1. Demonstrations

Generate controlled scenarios to showcase system capabilities.

### 2. Testing

Validate that the system correctly detects each type of discrepancy.

### 3. Benchmarking

Measure performance with different data volumes.

### 4. Training

Create exercises to train users.

## Considerations

### BC3 Encoding

BC3 files are saved in `latin-1` for compatibility with Presto.

### IFC Size

IFC modifications maintain similar size to the original.

### Reproducibility

Scenarios are deterministic - same input produces same output.
