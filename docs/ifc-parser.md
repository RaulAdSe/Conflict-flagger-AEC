# IFC Parser

## Description

The IFC Parser extracts data from BIM models in IFC (Industry Foundation Classes) format using the ifcopenshell library. Supports IFC2x3 and IFC4.

## Location

```
src/parsers/ifc_parser.py
```

## Main Classes

### IFCElement

Represents a BIM model element.

```python
@dataclass
class IFCElement:
    global_id: str              # IFC GUID (22 character base64)
    tag: Optional[str]          # Revit Tag (Element ID)
    name: str                   # Element name
    ifc_class: str              # IFC class (e.g., IfcColumn)

    # Type
    type_id: Optional[str]      # Type GUID
    type_name: Optional[str]    # Type name

    # Classification
    family_name: Optional[str]  # Revit family
    type_mark: Optional[str]    # Type mark

    # Data
    properties: dict            # Extracted properties
    quantities: dict            # Quantities (area, volume...)

    # Location
    level: Optional[str]        # Level/Story
    parent_id: Optional[str]    # Parent element
```

### IFCType

Represents a model type/family.

```python
@dataclass
class IFCType:
    global_id: str              # Type GUID
    tag: Optional[str]          # Type tag
    name: str                   # Full name
    ifc_class: str              # Class (e.g., IfcColumnType)

    family_name: Optional[str]  # Family name
    type_name: Optional[str]    # Type name

    properties: dict            # Type properties
    instance_count: int         # Number of instances
```

### IFCParseResult

```python
@dataclass
class IFCParseResult:
    elements: dict              # global_id -> IFCElement
    types: dict                 # global_id -> IFCType
    elements_by_tag: dict       # tag -> IFCElement
    types_by_tag: dict          # tag -> IFCType
    schema: str                 # IFC2X3 or IFC4
    project_name: str           # Project name
    errors: list                # Errors found
```

## Basic Usage

```python
from src.parsers.ifc_parser import IFCParser

parser = IFCParser()
result = parser.parse("model.ifc")

# Access elements
print(f"Schema: {result.schema}")
print(f"Project: {result.project_name}")
print(f"Elements: {len(result.elements)}")

# Iterate elements
for guid, element in result.elements.items():
    print(f"{element.ifc_class}: {element.name}")

# Find by tag (Revit ID)
element = result.elements_by_tag.get("350147")
```

## Supported IFC Classes

### Structural Elements

| IFC Class | Description |
|-----------|-------------|
| `IfcColumn` | Columns |
| `IfcBeam` | Beams |
| `IfcSlab` | Slabs/Floors |
| `IfcWall` | Walls |
| `IfcFooting` | Footings |
| `IfcPile` | Piles |

### Architectural Elements

| IFC Class | Description |
|-----------|-------------|
| `IfcDoor` | Doors |
| `IfcWindow` | Windows |
| `IfcStair` | Stairs |
| `IfcRailing` | Railings |
| `IfcRoof` | Roofs |
| `IfcCurtainWall` | Curtain walls |

### Other Elements

| IFC Class | Description |
|-----------|-------------|
| `IfcSpace` | Spaces |
| `IfcBuildingElementProxy` | Generic elements |
| `IfcFurnishingElement` | Furniture |

## Property Extraction

### Property Sets

The parser extracts properties from all PropertySets:

```python
# Access properties
element = result.elements[guid]
height = element.properties.get('Height')
material = element.properties.get('Material')
```

### Quantities

Extracts quantities from QuantitySets:

```python
# Available quantities
volume = element.quantities.get('NetVolume')
area = element.quantities.get('NetSideArea')
length = element.quantities.get('Length')
```

### Common Properties

| Property | Description |
|----------|-------------|
| `Height` | Height |
| `Width` | Width |
| `Length` | Length |
| `Material` | Material |
| `IsExternal` | If external |
| `LoadBearing` | If structural |
| `FireRating` | Fire rating |

## Type Hierarchy

```
IfcProject
└── IfcSite
    └── IfcBuilding
        └── IfcBuildingStorey
            └── IfcColumn (instance)
                └── relates to IfcColumnType
```

### Get Element Type

```python
element = result.elements[guid]
if element.type_id:
    element_type = result.types[element.type_id]
    print(f"Type: {element_type.name}")
```

### Get Type Instances

```python
def get_instances(parser, result, type_tag):
    return parser.get_elements_by_type_tag(result, type_tag)

instances = get_instances(parser, result, "350147")
print(f"Instances: {len(instances)}")
```

## Useful Methods

### get_elements_by_class()

```python
columns = parser.get_elements_by_class(result, 'IfcColumn')
beams = parser.get_elements_by_class(result, 'IfcBeam')
```

### get_elements_by_type_tag()

```python
# All instances of a type
instances = parser.get_elements_by_type_tag(result, type_tag)
```

## Name Parsing

Type names usually have format `Family:Type`:

```python
# Name: "Rectangular Column:600x600"
family, type_name = parser._parse_type_name(name)
# family = "Rectangular Column"
# type_name = "600x600"
```

## Error Handling

```python
try:
    result = parser.parse("model.ifc")
except FileNotFoundError:
    print("File not found")
except IOError as e:
    print(f"Error opening: {e}")

# Errors during parsing
for error in result.errors:
    print(f"Warning: {error}")
```

## Performance Considerations

### Large Files

For large IFC files (>100MB):

```python
# Parsing may take 10-30 seconds
# Consider showing progress bar
import time

start = time.time()
result = parser.parse("large_model.ifc")
print(f"Parsed in {time.time() - start:.1f}s")
```

### Memory

- ifcopenshell loads file into memory
- 500MB files may require 2-4GB RAM
- Consider batch processing for very large projects

## Revit Export

For best results when exporting from Revit:

1. **Use IFC4** when possible
2. **Include PropertySets** in export
3. **Export Quantities** (BaseQuantities)
4. **Keep Tags** visible in model

### Recommended Configuration

In Revit > Export > IFC Options:
- IFC Version: IFC4
- Export base quantities: Yes
- Export Revit property sets: Yes
- Export element GUID: Yes
