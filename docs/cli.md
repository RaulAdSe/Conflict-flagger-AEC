# CLI - Command Line Interface

## Description

The CLI provides a simple interface for running IFC-BC3 comparisons from the terminal.

## Location

```
src/main.py
```

## Basic Usage

```bash
python -m src.main --ifc model.ifc --bc3 budget.bc3
```

## Arguments

### Required

| Argument | Description |
|----------|-------------|
| `--ifc` | Path to IFC file (BIM model) |
| `--bc3` | Path to BC3 file (budget) |

### Optional

| Argument | Default | Description |
|----------|---------|-------------|
| `--output`, `-o` | `report_<timestamp>.xlsx` | Excel report output path |
| `--json` | - | Path for additional JSON report |
| `--tolerance` | `0.01` | Numeric tolerance (0.01 = 1%) |
| `--no-name-matching` | `False` | Disable name-based matching |
| `--verbose`, `-v` | `False` | Verbose output |
| `--quiet`, `-q` | `False` | Only show report path |

## Examples

### Simple Comparison

```bash
python -m src.main \
    --ifc data/input/model.ifc \
    --bc3 data/input/budget.bc3
```

### Custom Report Output

```bash
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    --output reports/january_comparison.xlsx
```

### With Additional JSON

```bash
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    --output report.xlsx \
    --json report.json
```

### Verbose Mode

```bash
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    -v
```

Shows the first 10 conflicts in terminal.

### Custom Tolerance

```bash
# 5% tolerance
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    --tolerance 0.05
```

### Quiet Mode

```bash
# Only shows report path
python -m src.main \
    --ifc model.ifc \
    --bc3 budget.bc3 \
    -q
```

Useful for automated scripts.

## Output

### Normal Mode

```
IFC file: model.ifc
BC3 file: budget.bc3
Output:   report.xlsx

Processing...
  Parsing IFC file...
  Parsing BC3 file...
  Matching elements...
  Comparing properties...
  Generating report...

============================================================
IFC-BC3 COMPARISON RESULTS
============================================================

MATCHING SUMMARY
  Total IFC types:     103
  Total BC3 elements:   68
  Matched:              47
  IFC only:             56 (not budgeted)
  BC3 only:             21 (orphan budget)
  Match rate:         55.0%

CONFLICT SUMMARY
  Total conflicts:     175
  Errors:               44
  Warnings:             77
  Property mismatches:  44

============================================================

Report saved to: report.xlsx
```

### Verbose Mode (-v)

Additionally shows:

```
TOP CONFLICTS:
  [350147] Height differs: IFC=0.6 BC3=0.8
  [350147] Width differs: IFC=0.6 BC3=0.8
  [350145] Element exists in IFC but not in BC3 budget
  ...
  ... and 165 more
```

### Quiet Mode (-q)

```
report.xlsx
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success with no errors |
| 1 | Execution error |
| 2 | Success but with detected errors |

### Usage in Scripts

```bash
python -m src.main --ifc model.ifc --bc3 budget.bc3 -q

if [ $? -eq 2 ]; then
    echo "Discrepancies detected!"
fi
```

## Integration

### Bash Script

```bash
#!/bin/bash

IFC_FILE="$1"
BC3_FILE="$2"
OUTPUT_DIR="reports/"

# Create directory if not exists
mkdir -p "$OUTPUT_DIR"

# Generate name with date
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}report_${TIMESTAMP}.xlsx"

# Run comparison
python -m src.main \
    --ifc "$IFC_FILE" \
    --bc3 "$BC3_FILE" \
    --output "$OUTPUT_FILE" \
    --json "${OUTPUT_FILE%.xlsx}.json"

# Open report
open "$OUTPUT_FILE"
```

### PowerShell (Windows)

```powershell
param(
    [string]$IfcFile,
    [string]$Bc3File
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$output = "reports\report_$timestamp.xlsx"

python -m src.main `
    --ifc $IfcFile `
    --bc3 $Bc3File `
    --output $output

if ($LASTEXITCODE -eq 0) {
    Start-Process $output
}
```

### Python

```python
import subprocess
import sys

result = subprocess.run([
    sys.executable, "-m", "src.main",
    "--ifc", "model.ifc",
    "--bc3", "budget.bc3",
    "--output", "report.xlsx",
    "-q"
], capture_output=True, text=True)

if result.returncode == 0:
    print(f"Report generated: {result.stdout.strip()}")
elif result.returncode == 2:
    print("Report generated with discrepancies")
else:
    print(f"Error: {result.stderr}")
```

## Help

```bash
python -m src.main --help
```

```
usage: main.py [-h] --ifc IFC --bc3 BC3 [--output OUTPUT] [--json JSON]
               [--tolerance TOLERANCE] [--no-name-matching] [--verbose] [--quiet]

Compare IFC model with BC3 budget and flag differences

optional arguments:
  -h, --help            show this help message and exit
  --ifc IFC             Path to IFC file
  --bc3 BC3             Path to BC3 file
  --output OUTPUT, -o OUTPUT
                        Output Excel report path
  --json JSON           Output JSON report path (optional)
  --tolerance TOLERANCE
                        Numeric tolerance for value comparison (default: 0.01)
  --no-name-matching    Disable fallback name-based matching
  --verbose, -v         Verbose output
  --quiet, -q           Quiet mode - only output file path

Examples:
  python -m src.main --ifc model.ifc --bc3 budget.bc3
  python -m src.main --ifc model.ifc --bc3 budget.bc3 --output report.xlsx
  python -m src.main --ifc model.ifc --bc3 budget.bc3 --json results.json
```

## Troubleshooting

### "IFC file not found"

```bash
# Check path
ls -la model.ifc

# Use absolute path
python -m src.main --ifc /full/path/model.ifc --bc3 budget.bc3
```

### "BC3 file not found"

```bash
# Check encoding
file budget.bc3
# Should be: ISO-8859-1 or UTF-8
```

### Memory Errors

```bash
# For very large IFC files
# Increase available memory or process in parts
```

### Permissions

```bash
# Linux/Mac: grant execute permissions
chmod +x src/main.py
```
