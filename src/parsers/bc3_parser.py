"""
BC3 Parser for FIEBDC-3 format files.

Extracts elements with their properties, IFC GUIDs, and hierarchy information.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BC3Element:
    """Represents an element extracted from a BC3 file."""

    code: str
    unit: str
    description: str
    price: float

    # IFC linking
    ifc_guid: Optional[str] = None  # Instance GUID
    type_ifc_guid: Optional[str] = None  # Type GUID (Tipo IfcGUID)

    # Classification
    family_name: Optional[str] = None  # Nombre de familia
    type_name: Optional[str] = None  # Nombre de tipo

    # Properties from ~X records
    properties: dict = field(default_factory=dict)

    # Hierarchy
    parent_code: Optional[str] = None
    children: list = field(default_factory=list)
    quantity: float = 0.0

    def __post_init__(self):
        # Ensure properties is a dict
        if self.properties is None:
            self.properties = {}
        if self.children is None:
            self.children = []


@dataclass
class BC3ParseResult:
    """Result of parsing a BC3 file."""

    elements: dict  # code -> BC3Element
    hierarchy: dict  # parent_code -> [(child_code, quantity), ...]
    version: str
    errors: list = field(default_factory=list)


class BC3Parser:
    """Parser for FIEBDC-3 (.bc3) format files."""

    # Record type patterns
    RECORD_PATTERN = re.compile(r'^~([A-Z])\|(.*)$')

    # Known property mappings (Spanish -> English)
    PROPERTY_MAPPINGS = {
        'Nombre de familia': 'family_name',
        'Nombre de tipo': 'type_name',
        'Tipo IfcGUID': 'type_ifc_guid',
        'IfcGUID': 'ifc_guid',
        'Anchura': 'width',
        'Altura': 'height',
        'Grosor': 'thickness',
        'Material': 'material',
        'Longitud': 'length',
    }

    def __init__(self, encoding: str = 'latin-1'):
        self.encoding = encoding

    def parse(self, file_path: str | Path) -> BC3ParseResult:
        """
        Parse a BC3 file and extract all elements with their properties.

        Args:
            file_path: Path to the BC3 file

        Returns:
            BC3ParseResult with elements and hierarchy
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"BC3 file not found: {file_path}")

        elements: dict[str, BC3Element] = {}
        hierarchy: dict[str, list] = {}
        version = ""
        errors = []

        # Read file content
        try:
            content = file_path.read_text(encoding=self.encoding, errors='replace')
        except Exception as e:
            raise IOError(f"Error reading BC3 file: {e}")

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            match = self.RECORD_PATTERN.match(line)
            if not match:
                continue

            record_type = match.group(1)
            record_data = match.group(2)

            try:
                if record_type == 'V':
                    version = self._parse_version(record_data)
                elif record_type == 'C':
                    element = self._parse_component(record_data)
                    if element:
                        elements[element.code] = element
                elif record_type == 'X':
                    self._parse_extended(record_data, elements)
                elif record_type == 'D':
                    self._parse_decomposition(record_data, hierarchy)
            except Exception as e:
                errors.append(f"Line {line_num}: {e}")

        # Link hierarchy to elements
        self._link_hierarchy(elements, hierarchy)

        return BC3ParseResult(
            elements=elements,
            hierarchy=hierarchy,
            version=version,
            errors=errors
        )

    def _parse_version(self, data: str) -> str:
        """Parse ~V record for version info."""
        parts = data.split('|')
        if len(parts) >= 2:
            return parts[1] if parts[1] else parts[0]
        return parts[0] if parts else ""

    def _parse_component(self, data: str) -> Optional[BC3Element]:
        """
        Parse ~C record for component definition.

        Format: ~C|Code#|Unit|Description|Price|Date|Type|
        """
        parts = data.split('|')
        if len(parts) < 4:
            return None

        # Clean code (remove trailing #)
        code = parts[0].rstrip('#').strip()
        if not code:
            return None

        unit = parts[1].strip() if len(parts) > 1 else ""
        description = parts[2].strip() if len(parts) > 2 else ""

        # Parse price (handle comma as decimal separator)
        price = 0.0
        if len(parts) > 3 and parts[3].strip():
            try:
                price_str = parts[3].strip().replace(',', '.')
                price = float(price_str)
            except ValueError:
                price = 0.0

        return BC3Element(
            code=code,
            unit=unit,
            description=description,
            price=price
        )

    def _parse_extended(self, data: str, elements: dict[str, BC3Element]) -> None:
        r"""
        Parse ~X record for extended properties.

        Format: ~X|Code|PropName\PropValue\PropName\PropValue\...|
        """
        parts = data.split('|')
        if len(parts) < 2:
            return

        code = parts[0].strip()
        if code not in elements:
            return

        element = elements[code]
        props_data = parts[1] if len(parts) > 1 else ""

        # Parse properties (backslash-separated key\value pairs)
        props = props_data.split('\\')

        i = 0
        while i < len(props) - 1:
            key = props[i].strip()
            value = props[i + 1].strip() if i + 1 < len(props) else ""

            if key:
                # Handle special properties
                if key == 'Tipo IfcGUID':
                    element.type_ifc_guid = value
                elif key == 'IfcGUID':
                    element.ifc_guid = value
                elif key == 'Nombre de familia':
                    element.family_name = value
                elif key == 'Nombre de tipo':
                    element.type_name = value
                else:
                    # Store as generic property
                    element.properties[key] = self._parse_property_value(value)

            i += 2

    def _parse_property_value(self, value: str):
        """Parse a property value, converting to appropriate type."""
        if not value:
            return None

        # Try to parse as number
        try:
            if '.' in value or ',' in value:
                return float(value.replace(',', '.'))
            return int(value)
        except ValueError:
            pass

        return value

    def _parse_decomposition(self, data: str, hierarchy: dict) -> None:
        r"""
        Parse ~D record for hierarchy/decomposition.

        Format: ~D|ParentCode#|ChildCode\Factor\Quantity\ChildCode\Factor\Quantity\...|
        """
        parts = data.split('|')
        if len(parts) < 2:
            return

        parent_code = parts[0].rstrip('#').strip()
        if not parent_code:
            return

        children_data = parts[1] if len(parts) > 1 else ""
        children_parts = children_data.split('\\')

        children = []
        i = 0
        while i < len(children_parts):
            child_code = children_parts[i].strip()
            if not child_code:
                i += 1
                continue

            # Get quantity (usually at position i+2)
            quantity = 1.0
            if i + 2 < len(children_parts):
                try:
                    qty_str = children_parts[i + 2].strip().replace(',', '.')
                    if qty_str:
                        quantity = float(qty_str)
                except (ValueError, IndexError):
                    pass

            children.append((child_code, quantity))
            i += 3  # Move to next child (code, factor, quantity)

        if children:
            hierarchy[parent_code] = children

    def _link_hierarchy(self, elements: dict[str, BC3Element], hierarchy: dict) -> None:
        """Link parent-child relationships in elements."""
        for parent_code, children in hierarchy.items():
            if parent_code in elements:
                parent = elements[parent_code]
                for child_code, quantity in children:
                    parent.children.append((child_code, quantity))
                    if child_code in elements:
                        elements[child_code].parent_code = parent_code
                        elements[child_code].quantity = quantity

    def get_types_with_guid(self, result: BC3ParseResult) -> dict[str, BC3Element]:
        """
        Get all elements that have a Type IFC GUID.

        These are the type-level elements that can be matched to IFC types.
        """
        return {
            code: elem for code, elem in result.elements.items()
            if elem.type_ifc_guid
        }

    def get_elements_by_family(self, result: BC3ParseResult, family_name: str) -> list[BC3Element]:
        """Get all elements belonging to a specific family."""
        return [
            elem for elem in result.elements.values()
            if elem.family_name and family_name.lower() in elem.family_name.lower()
        ]
