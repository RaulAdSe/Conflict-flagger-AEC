# BC3 Parser

## Description

The BC3 Parser extracts data from budget files in BC3 format (FIEBDC-3). This format is the standard in Spain for construction database exchange.

## Location

```
src/parsers/bc3_parser.py
```

## Main Classes

### BC3Element

Represents a budget line item.

```python
@dataclass
class BC3Element:
    code: str                    # Unique code (e.g., "350147")
    unit: str                    # Unit (m2, m3, u, kg...)
    description: str             # Line item description
    price: float                 # Unit price

    # Classification
    family_name: Optional[str]   # Family (e.g., "Column", "Beam")
    type_name: Optional[str]     # Type (e.g., "600x600", "HEB200")

    # Extended properties
    properties: dict             # Properties from ~X record

    # IFC linking
    ifc_guid: Optional[str]      # IFC GlobalId if available

    # Hierarchy
    parent_code: Optional[str]   # Parent code
    children_codes: list         # Children codes
```

### BC3ParseResult

Result of parsing a BC3 file.

```python
@dataclass
class BC3ParseResult:
    elements: dict              # code -> BC3Element
    elements_by_guid: dict      # ifc_guid -> BC3Element
    hierarchy: dict             # code -> [children_codes]
    version: str                # Format version
    errors: list                # Errors found
```

## Basic Usage

```python
from src.parsers.bc3_parser import BC3Parser

parser = BC3Parser()
result = parser.parse("budget.bc3")

# Access elements
for code, element in result.elements.items():
    print(f"{code}: {element.description} - {element.price} EUR")

# Find by IFC GUID
if guid in result.elements_by_guid:
    element = result.elements_by_guid[guid]
```

## BC3 Format

### Record Structure

BC3 format uses records starting with `~` followed by a letter:

| Record | Description |
|--------|-------------|
| `~V` | Format version |
| `~K` | Coefficients |
| `~C` | Concept (line item) |
| `~D` | Decomposition |
| `~T` | Descriptive text |
| `~X` | Extended properties |

### Example ~C Record

```
~C|350147#|m3|Reinforced concrete column HA-25|150.50|999999|0|
```

Fields:
1. Code (`350147#`)
2. Unit (`m3`)
3. Description
4. Price
5. Date
6. Type

### Example ~X Record

```
~X|350147|Number\200\GUID_IFC\3n$x...\\h\0.6\\b\0.6\|
```

Extended properties with format `name\value\`.

## Property Extraction

### Dimensional Properties

The parser automatically extracts:

- `h` - Height
- `b` - Width/Base
- `L` - Length
- `e` - Thickness

### IFC GUID

Searches for GUID in properties:

```python
# Searches in extended properties
guid = element.properties.get('GUID_IFC') or \
       element.properties.get('IfcGUID') or \
       element.properties.get('GlobalId')
```

## Hierarchy

BC3 has hierarchical structure:

```
Chapter
└── Subchapter
    └── Line item
        └── Sub-item
```

The parser maintains this hierarchy:

```python
# Get children of an element
children = result.hierarchy.get(parent_code, [])

# Get parent
parent = result.elements[element.parent_code]
```

## Error Handling

```python
result = parser.parse("file.bc3")

if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

Common errors:
- File not found
- Incorrect encoding (tries latin-1)
- Malformed records

## Useful Methods

### get_types_with_guid()

Gets only elements with IFC GUID:

```python
types_with_guid = parser.get_types_with_guid(result)
for element in types_with_guid:
    print(f"{element.code}: {element.ifc_guid}")
```

### get_elements_by_family()

Groups elements by family:

```python
by_family = parser.get_elements_by_family(result)
for family, elements in by_family.items():
    print(f"{family}: {len(elements)} elements")
```

## Considerations

### Encoding

BC3 files usually use `latin-1` (ISO-8859-1) encoding. The parser tries:

1. UTF-8
2. latin-1
3. cp1252 (Windows)

### File Size

For large files (>10MB):
- Parsing may take several seconds
- Consider showing progress to user

### Compatibility

Compatible with:
- Presto
- Arquimedes
- TCQ
- Other programs that export FIEBDC-3
