"""
IFC Parser using ifcopenshell.

Extracts elements with their GlobalId, Tag, properties for matching with BC3.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import ifcopenshell
import ifcopenshell.util.element as element_util


@dataclass
class IFCElement:
    """Represents an element extracted from an IFC file."""

    global_id: str  # IFC GlobalId (22 character base64)
    tag: Optional[str]  # Revit Element ID
    name: str
    ifc_class: str  # e.g., IfcColumn, IfcBeam, IfcWall

    # Type information
    type_id: Optional[str] = None  # Type GlobalId
    type_name: Optional[str] = None

    # Classification
    family_name: Optional[str] = None
    type_mark: Optional[str] = None

    # Properties
    properties: dict = field(default_factory=dict)

    # Quantities
    quantities: dict = field(default_factory=dict)

    # Hierarchy
    level: Optional[str] = None
    parent_id: Optional[str] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.quantities is None:
            self.quantities = {}


@dataclass
class IFCType:
    """Represents a type definition from an IFC file."""

    global_id: str
    tag: Optional[str]  # Type ID from Revit
    name: str
    ifc_class: str  # e.g., IfcColumnType, IfcBeamType

    # Classification
    family_name: Optional[str] = None
    type_name: Optional[str] = None

    # Properties
    properties: dict = field(default_factory=dict)

    # Instance count
    instance_count: int = 0

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class IFCParseResult:
    """Result of parsing an IFC file."""

    elements: dict  # global_id -> IFCElement
    types: dict  # global_id -> IFCType
    elements_by_tag: dict  # tag -> IFCElement
    types_by_tag: dict  # tag -> IFCType
    schema: str
    project_name: str
    errors: list = field(default_factory=list)


class IFCParser:
    """Parser for IFC files using ifcopenshell."""

    # Element types we're interested in
    ELEMENT_TYPES = [
        'IfcWall', 'IfcWallStandardCase',
        'IfcColumn',
        'IfcBeam',
        'IfcSlab',
        'IfcDoor',
        'IfcWindow',
        'IfcStair', 'IfcStairFlight',
        'IfcRailing',
        'IfcRoof',
        'IfcCovering',
        'IfcCurtainWall',
        'IfcMember',
        'IfcPlate',
        'IfcFooting',
        'IfcPile',
        'IfcRamp', 'IfcRampFlight',
        'IfcBuildingElementProxy',
        'IfcSpace',
        'IfcFurnishingElement',
        'IfcFlowTerminal',
        'IfcFlowSegment',
    ]

    def __init__(self):
        self.ifc_file = None

    def parse(self, file_path: str | Path) -> IFCParseResult:
        """
        Parse an IFC file and extract elements with their properties.

        Args:
            file_path: Path to the IFC file

        Returns:
            IFCParseResult with elements and types
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        try:
            self.ifc_file = ifcopenshell.open(str(file_path))
        except Exception as e:
            raise IOError(f"Error opening IFC file: {e}")

        elements: dict[str, IFCElement] = {}
        types: dict[str, IFCType] = {}
        elements_by_tag: dict[str, IFCElement] = {}
        types_by_tag: dict[str, IFCType] = {}
        errors = []

        # Get schema and project info
        schema = self.ifc_file.schema
        project_name = self._get_project_name()

        # Parse type definitions first
        self._parse_types(types, types_by_tag, errors)

        # Parse elements
        self._parse_elements(elements, elements_by_tag, types, errors)

        return IFCParseResult(
            elements=elements,
            types=types,
            elements_by_tag=elements_by_tag,
            types_by_tag=types_by_tag,
            schema=schema,
            project_name=project_name,
            errors=errors
        )

    def _get_project_name(self) -> str:
        """Get the project name from IFC."""
        try:
            project = self.ifc_file.by_type('IfcProject')[0]
            return project.Name or ""
        except (IndexError, AttributeError):
            return ""

    def _parse_types(self, types: dict, types_by_tag: dict, errors: list) -> None:
        """Parse all type definitions."""
        type_classes = [
            'IfcWallType', 'IfcColumnType', 'IfcBeamType', 'IfcSlabType',
            'IfcDoorType', 'IfcWindowType', 'IfcStairType', 'IfcRailingType',
            'IfcRoofType', 'IfcCoveringType', 'IfcCurtainWallType',
            'IfcMemberType', 'IfcPlateType', 'IfcFootingType', 'IfcPileType',
            'IfcBuildingElementProxyType', 'IfcFurnitureType',
            'IfcSpaceType',
        ]

        for type_class in type_classes:
            try:
                for ifc_type in self.ifc_file.by_type(type_class):
                    try:
                        parsed_type = self._parse_single_type(ifc_type)
                        if parsed_type:
                            types[parsed_type.global_id] = parsed_type
                            if parsed_type.tag:
                                types_by_tag[parsed_type.tag] = parsed_type
                    except Exception as e:
                        errors.append(f"Error parsing type {type_class}: {e}")
            except RuntimeError:
                # Type class not in this schema
                continue

    def _parse_single_type(self, ifc_type) -> Optional[IFCType]:
        """Parse a single IFC type definition."""
        global_id = ifc_type.GlobalId
        name = ifc_type.Name or ""

        # Get tag (usually the last attribute or from Tag property)
        tag = getattr(ifc_type, 'Tag', None)

        # Parse name to extract family and type
        family_name, type_name = self._parse_type_name(name)

        # Get properties
        properties = self._get_properties(ifc_type)

        return IFCType(
            global_id=global_id,
            tag=tag,
            name=name,
            ifc_class=ifc_type.is_a(),
            family_name=family_name,
            type_name=type_name,
            properties=properties
        )

    def _parse_elements(self, elements: dict, elements_by_tag: dict,
                        types: dict, errors: list) -> None:
        """Parse all building elements."""
        for element_class in self.ELEMENT_TYPES:
            try:
                for ifc_element in self.ifc_file.by_type(element_class):
                    try:
                        parsed = self._parse_single_element(ifc_element, types)
                        if parsed:
                            elements[parsed.global_id] = parsed
                            if parsed.tag:
                                elements_by_tag[parsed.tag] = parsed
                    except Exception as e:
                        errors.append(f"Error parsing {element_class}: {e}")
            except RuntimeError:
                # Element class not in this schema
                continue

    def _parse_single_element(self, ifc_element, types: dict) -> Optional[IFCElement]:
        """Parse a single IFC element."""
        global_id = ifc_element.GlobalId
        name = ifc_element.Name or ""

        # Get tag
        tag = getattr(ifc_element, 'Tag', None)

        # Get type information
        type_id = None
        type_name = None
        family_name = None

        try:
            element_type = element_util.get_type(ifc_element)
            if element_type:
                type_id = element_type.GlobalId
                type_name = element_type.Name

                # Update instance count
                if type_id in types:
                    types[type_id].instance_count += 1

                # Parse names
                family_name, type_name = self._parse_type_name(type_name or name)
        except Exception:
            family_name, type_name = self._parse_type_name(name)

        # Get properties and quantities
        properties = self._get_properties(ifc_element)
        quantities = self._get_quantities(ifc_element)

        # Get level
        level = self._get_level(ifc_element)

        return IFCElement(
            global_id=global_id,
            tag=tag,
            name=name,
            ifc_class=ifc_element.is_a(),
            type_id=type_id,
            type_name=type_name,
            family_name=family_name,
            properties=properties,
            quantities=quantities,
            level=level
        )

    def _parse_type_name(self, name: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse a type name like 'FamilyName:TypeName' into components.

        Returns:
            Tuple of (family_name, type_name)
        """
        if not name:
            return None, None

        if ':' in name:
            parts = name.split(':', 1)
            return parts[0].strip(), parts[1].strip()

        return name, None

    def _get_properties(self, ifc_entity) -> dict:
        """Extract properties from an IFC entity."""
        properties = {}

        try:
            # Get property sets
            if hasattr(ifc_entity, 'IsDefinedBy'):
                for rel in ifc_entity.IsDefinedBy:
                    if rel.is_a('IfcRelDefinesByProperties'):
                        prop_set = rel.RelatingPropertyDefinition
                        if prop_set.is_a('IfcPropertySet'):
                            for prop in prop_set.HasProperties:
                                if prop.is_a('IfcPropertySingleValue'):
                                    value = self._get_property_value(prop)
                                    if value is not None:
                                        properties[prop.Name] = value

            # Also check for type properties
            if hasattr(ifc_entity, 'HasPropertySets'):
                for prop_set in ifc_entity.HasPropertySets or []:
                    if prop_set.is_a('IfcPropertySet'):
                        for prop in prop_set.HasProperties:
                            if prop.is_a('IfcPropertySingleValue'):
                                value = self._get_property_value(prop)
                                if value is not None:
                                    properties[prop.Name] = value

        except Exception:
            pass

        return properties

    def _get_property_value(self, prop):
        """Extract value from an IfcPropertySingleValue."""
        try:
            nominal_value = prop.NominalValue
            if nominal_value is None:
                return None

            # Handle wrapped values
            if hasattr(nominal_value, 'wrappedValue'):
                return nominal_value.wrappedValue

            return nominal_value
        except Exception:
            return None

    def _get_quantities(self, ifc_entity) -> dict:
        """Extract quantities from an IFC entity."""
        quantities = {}

        try:
            if hasattr(ifc_entity, 'IsDefinedBy'):
                for rel in ifc_entity.IsDefinedBy:
                    if rel.is_a('IfcRelDefinesByProperties'):
                        prop_def = rel.RelatingPropertyDefinition
                        if prop_def.is_a('IfcElementQuantity'):
                            for qty in prop_def.Quantities:
                                qty_value = self._get_quantity_value(qty)
                                if qty_value is not None:
                                    quantities[qty.Name] = qty_value
        except Exception:
            pass

        return quantities

    def _get_quantity_value(self, qty):
        """Extract value from an IFC quantity."""
        try:
            if qty.is_a('IfcQuantityLength'):
                return qty.LengthValue
            elif qty.is_a('IfcQuantityArea'):
                return qty.AreaValue
            elif qty.is_a('IfcQuantityVolume'):
                return qty.VolumeValue
            elif qty.is_a('IfcQuantityWeight'):
                return qty.WeightValue
            elif qty.is_a('IfcQuantityCount'):
                return qty.CountValue
        except Exception:
            pass
        return None

    def _get_level(self, ifc_entity) -> Optional[str]:
        """Get the building storey/level of an element."""
        try:
            if hasattr(ifc_entity, 'ContainedInStructure'):
                for rel in ifc_entity.ContainedInStructure:
                    structure = rel.RelatingStructure
                    if structure.is_a('IfcBuildingStorey'):
                        return structure.Name
        except Exception:
            pass
        return None

    def get_elements_by_type_tag(self, result: IFCParseResult, type_tag: str) -> list[IFCElement]:
        """Get all instances of a type by its tag."""
        if type_tag not in result.types_by_tag:
            return []

        ifc_type = result.types_by_tag[type_tag]
        return [
            elem for elem in result.elements.values()
            if elem.type_id == ifc_type.global_id
        ]

    def get_elements_by_class(self, result: IFCParseResult, ifc_class: str) -> list[IFCElement]:
        """Get all elements of a specific IFC class."""
        return [
            elem for elem in result.elements.values()
            if elem.ifc_class == ifc_class or elem.ifc_class.startswith(ifc_class)
        ]
