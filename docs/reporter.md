# Reporter

## Description

The Reporter generates visual reports in Excel and JSON from comparison results. Reports are output in **Spanish** for end-users in the Spanish AEC market, with color coding for easy problem identification.

## Location

```
src/reporting/reporter.py
```

## Output Formats

### Excel (.xlsx)

Visual report with multiple sheets:

| Sheet | Content |
|-------|---------|
| Resumen | General statistics and status |
| Discrepancias | Detail of all conflicts |
| Elementos Emparejados | List of linked elements |
| Sin Presupuestar | IFC elements without BC3 item |
| Sin Modelar | BC3 items without IFC element |

### JSON (.json)

Structured data for integration:

```json
{
  "resumen": {
    "fecha_generacion": "2024-01-15T10:30:00",
    "emparejamiento": {...},
    "comparacion": {...}
  },
  "discrepancias": [...],
  "emparejados": [...],
  "solo_ifc": [...],
  "solo_bc3": [...]
}
```

## Basic Usage

```python
from src.reporting.reporter import Reporter

reporter = Reporter()

# Generate Excel
report_path = reporter.generate_report(
    match_result,
    comparison_result,
    "report.xlsx"
)

# Generate JSON
json_data = reporter.generate_json_report(
    match_result,
    comparison_result
)
```

## Configuration

### ReportConfig

```python
from src.reporting.reporter import Reporter, ReportConfig

config = ReportConfig(
    color_error="FF6B6B",      # Soft red
    color_warning="FFE66D",    # Soft yellow
    color_ok="7ED957",         # Soft green
    color_info="74C0FC",       # Soft blue
    color_header="2E86AB",     # Corporate blue
    show_ok_matches=True,      # Show elements without conflict
    show_info_conflicts=False, # Hide INFO conflicts
    max_rows=10000             # Maximum rows per sheet
)

reporter = Reporter(config)
```

## Excel Sheets

### 1. Resumen (Summary)

Contains:
- Title and report information
- Generation date
- Overall status (color-coded)
- Matching statistics
- Comparison statistics
- Color legend

```
┌────────────────────────────────────────────┐
│  INFORME DE COMPARACION IFC - BC3          │
│  Generado: 15/01/2024 10:30                │
├────────────────────────────────────────────┤
│  RESUMEN EJECUTIVO                         │
│  ┌──────────────────────────────────────┐  │
│  │ 5 errores y 12 avisos detectados    │  │ ← Color-coded
│  └──────────────────────────────────────┘  │
├────────────────────────────────────────────┤
│  ESTADISTICAS DE EMPAREJAMIENTO            │
│  Tipos en modelo IFC:        103           │
│  Partidas en presupuesto:     68           │
│  Emparejados:                 47           │
│  Tasa de emparejamiento:    55.0%          │
└────────────────────────────────────────────┘
```

### 2. Discrepancias (Discrepancies)

Detailed list of conflicts:

| Column | Description |
|--------|-------------|
| Codigo | Element code |
| Elemento | Element name |
| Tipo de Discrepancia | Conflict type (translated) |
| Gravedad | ERROR / AVISO |
| Propiedad | Affected property |
| Valor IFC | Value in model |
| Valor BC3 | Value in budget |
| Descripcion | Explanatory message |

Colors:
- Red: Errors
- Yellow: Warnings

### 3. Elementos Emparejados (Matched Elements)

| Column | Description |
|--------|-------------|
| Codigo/Tag | Identifier |
| Nombre en IFC | IFC type name |
| Descripcion en BC3 | Item description |
| Metodo de Emparejamiento | GUID / Tag / Name |
| Estado | Correct / N discrepancies |
| Num. Discrepancias | Number of conflicts |

Colors:
- Green: No conflicts
- Red: Has conflicts

### 4. Sin Presupuestar (Not Budgeted)

IFC elements without BC3 item:

| Column | Description |
|--------|-------------|
| Codigo/Tag | Element ID |
| Nombre | IFC name |
| Clase IFC | Element type |
| Familia | Revit family |
| Tipo | Type name |
| Accion Requerida | "Incluir en presupuesto BC3" |

### 5. Sin Modelar (Not Modeled)

BC3 items without IFC element:

| Column | Description |
|--------|-------------|
| Codigo | Item code |
| Descripcion | BC3 description |
| Unidad | Unit of measure |
| Precio | Unit price |
| Familia | Family |
| Accion Requerida | "Modelar en IFC o eliminar" |

## Translations

The reporter automatically translates to Spanish:

| English | Spanish |
|---------|---------|
| property_mismatch | Diferencia de valor |
| missing_in_bc3 | Falta en presupuesto |
| missing_in_ifc | Falta en modelo |
| error | ERROR |
| warning | AVISO |
| guid | Por GUID |
| tag | Por Tag/ID |

## Complete Example

```python
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter, ReportConfig

# Complete pipeline
ifc_result = IFCParser().parse("model.ifc")
bc3_result = BC3Parser().parse("budget.bc3")
match_result = Matcher().match(ifc_result, bc3_result)
comparison = Comparator().compare(match_result)

# Configure report
config = ReportConfig(
    show_ok_matches=True,
    max_rows=5000
)
reporter = Reporter(config)

# Generate Excel
excel_path = reporter.generate_report(
    match_result,
    comparison,
    "comparison_report.xlsx"
)
print(f"Excel generated: {excel_path}")

# Generate JSON
import json
json_data = reporter.generate_json_report(match_result, comparison)
with open("comparison_report.json", "w") as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)
```

## Color Customization

```python
# Custom corporate colors
config = ReportConfig(
    color_error="E74C3C",      # Corporate red
    color_warning="F39C12",    # Orange
    color_ok="27AE60",         # Corporate green
    color_header="34495E"      # Dark gray
)
```

## Integration with Other Systems

### Export to DataFrame

```python
import pandas as pd

# Conflicts as DataFrame
conflicts_data = [
    {
        "code": c.code,
        "element": c.element_name,
        "type": c.conflict_type.value,
        "severity": c.severity.value,
        "property": c.property_name,
        "ifc_value": c.ifc_value,
        "bc3_value": c.bc3_value
    }
    for c in comparison.conflicts
]

df = pd.DataFrame(conflicts_data)
df.to_excel("conflicts.xlsx", index=False)
```

### Send by Email

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

# Generate report
report_path = reporter.generate_report(...)

# Attach to email
msg = MIMEMultipart()
with open(report_path, "rb") as f:
    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(f.read())
    msg.attach(attachment)
```

## Considerations

### Performance

- Files with >10,000 conflicts may take time to generate
- Use `max_rows` to limit if necessary

### Compatibility

- Excel 2010+
- LibreOffice Calc
- Google Sheets (import .xlsx)
