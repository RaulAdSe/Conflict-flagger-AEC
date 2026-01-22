"""
IFC Parser - CLEAN VERSION

Extracts types and elements from IFC files with proper quantity aggregation.

KEY BEHAVIORS:
1. Consolidates types with same Tag (Revit exports duplicates)
2. Aggregates quantities from all instances to their type
3. Does NOT divide wall areas (Cost-It measures both faces)
4. Caches parsed results for faster subsequent loads
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List
import ifcopenshell
import ifcopenshell.util.element as element_util

# Global cache for parsed IFC results
# Key: (file_path, file_mtime, file_size) -> IFCParseResult
_IFC_CACHE: Dict[tuple, 'IFCParseResult'] = {}


@dataclass
class IFCElement:
    """Represents an element instance from an IFC file."""
    global_id: str
    tag: Optional[str]
    name: str
    ifc_class: str
    type_id: Optional[str] = None
    type_name: Optional[str] = None
    family_name: Optional[str] = None
    properties: dict = field(default_factory=dict)
    quantities: dict = field(default_factory=dict)
    level: Optional[str] = None


@dataclass
class IFCType:
    """Represents a type definition from an IFC file."""
    global_id: str
    tag: Optional[str]
    name: str
    ifc_class: str
    family_name: Optional[str] = None
    type_name: Optional[str] = None
    properties: dict = field(default_factory=dict)
    quantities: dict = field(default_factory=dict)
    instance_count: int = 0
    # Track consolidated type GlobalIds
    consolidated_ids: List[str] = field(default_factory=list)
    # Track how many instances have each quantity (for detecting incomplete exports)
    # Format: {quantity_name: count_of_instances_with_this_quantity}
    quantity_coverage: dict = field(default_factory=dict)


@dataclass
class IFCParseResult:
    """Result of parsing an IFC file."""
    elements: Dict[str, IFCElement]
    types: Dict[str, IFCType]
    elements_by_tag: Dict[str, IFCElement]
    types_by_tag: Dict[str, IFCType]
    schema: str
    project_name: str
    errors: List[str] = field(default_factory=list)


class IFCParser:
    """Parser for IFC files using ifcopenshell."""

    ELEMENT_TYPES = [
        'IfcWall',  # Includes IfcWallStandardCase
        'IfcColumn', 'IfcBeam', 'IfcSlab',
        'IfcDoor', 'IfcWindow',
        'IfcStair',  # Includes IfcStairFlight
        'IfcRailing', 'IfcRoof',
        'IfcCovering', 'IfcCurtainWall',
        'IfcMember', 'IfcPlate',
        'IfcFooting', 'IfcPile',
        'IfcRamp',  # Includes IfcRampFlight
        'IfcBuildingElementProxy',
        'IfcSpace',
        'IfcFurnishingElement',
        'IfcFlowTerminal', 'IfcFlowSegment',
    ]

    def __init__(self):
        self.ifc_file = None

    def _get_cache_key(self, file_path: Path) -> tuple:
        """Generate a cache key based on file path, mtime, and size."""
        stat = file_path.stat()
        return (str(file_path.absolute()), stat.st_mtime, stat.st_size)

    def parse(self, file_path: str | Path, use_cache: bool = True) -> IFCParseResult:
        """Parse an IFC file and extract elements with their properties.

        Args:
            file_path: Path to the IFC file
            use_cache: If True, use cached results for unchanged files (default: True)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        # Check cache for unchanged files
        if use_cache:
            cache_key = self._get_cache_key(file_path)
            if cache_key in _IFC_CACHE:
                return _IFC_CACHE[cache_key]

        self.ifc_file = ifcopenshell.open(str(file_path))

        errors = []
        schema = self.ifc_file.schema
        project_name = self._get_project_name()

        # Step 1: Parse type definitions
        raw_types = self._parse_types(errors)
        
        # Step 2: Consolidate types by Tag
        types, types_by_tag = self._consolidate_types(raw_types)
        
        # Step 3: Parse elements and aggregate to types
        elements, elements_by_tag = self._parse_elements(types, types_by_tag, errors)

        result = IFCParseResult(
            elements=elements,
            types=types,
            elements_by_tag=elements_by_tag,
            types_by_tag=types_by_tag,
            schema=schema,
            project_name=project_name,
            errors=errors
        )

        # Cache the result for future use
        if use_cache:
            cache_key = self._get_cache_key(file_path)
            _IFC_CACHE[cache_key] = result

        return result

    def _get_project_name(self) -> str:
        """Get the project name from IFC."""
        try:
            project = self.ifc_file.by_type('IfcProject')[0]
            return project.Name or ""
        except (IndexError, AttributeError):
            return ""

    def _parse_types(self, errors: list) -> Dict[str, IFCType]:
        """Parse all type definitions (raw, before consolidation)."""
        # Specific type classes to parse
        type_classes = [
            'IfcWallType', 'IfcColumnType', 'IfcBeamType', 'IfcSlabType',
            'IfcDoorType', 'IfcWindowType', 'IfcStairType', 'IfcRailingType',
            'IfcRoofType', 'IfcCoveringType', 'IfcCurtainWallType',
            'IfcMemberType', 'IfcPlateType', 'IfcFootingType', 'IfcPileType',
            'IfcBuildingElementProxyType', 'IfcFurnitureType', 'IfcSpaceType',
            # IFC2x3 style classes (used instead of Type classes)
            'IfcDoorStyle', 'IfcWindowStyle',
            # Additional type classes
            'IfcStairFlightType', 'IfcRampFlightType',
        ]

        types = {}

        for type_class in type_classes:
            try:
                for ifc_type in self.ifc_file.by_type(type_class):
                    try:
                        parsed = self._parse_single_type(ifc_type)
                        if parsed:
                            types[parsed.global_id] = parsed
                    except Exception as e:
                        errors.append(f"Error parsing {type_class}: {e}")
            except RuntimeError:
                continue

        # Also parse generic IfcTypeProduct to catch any types not covered above
        # (e.g., Revit sometimes exports types as generic IfcTypeProduct)
        try:
            for ifc_type in self.ifc_file.by_type('IfcTypeProduct'):
                if ifc_type.GlobalId not in types:  # Only if not already parsed
                    try:
                        parsed = self._parse_single_type(ifc_type)
                        if parsed:
                            types[parsed.global_id] = parsed
                    except Exception as e:
                        errors.append(f"Error parsing IfcTypeProduct: {e}")
        except RuntimeError:
            pass

        return types

    def _parse_single_type(self, ifc_type) -> Optional[IFCType]:
        """Parse a single IFC type definition."""
        global_id = ifc_type.GlobalId
        name = ifc_type.Name or ""
        tag = getattr(ifc_type, 'Tag', None)
        family_name, type_name = self._parse_type_name(name)
        properties = self._get_properties(ifc_type)

        return IFCType(
            global_id=global_id,
            tag=tag,
            name=name,
            ifc_class=ifc_type.is_a(),
            family_name=family_name,
            type_name=type_name,
            properties=properties,
            consolidated_ids=[global_id]
        )

    def _consolidate_types(self, raw_types: Dict[str, IFCType]):
        """
        Consolidate types with the same Tag into one entry.
        
        Revit can export multiple type entities with the same Tag.
        We consolidate them to avoid counting the same type multiple times.
        
        IMPORTANT: The returned `types` dict only contains ONE entry per Tag,
        not multiple entries pointing to the same object.
        """
        types = {}
        types_by_tag = {}
        
        # Group by tag
        by_tag = {}
        no_tag = []
        
        for gid, ifc_type in raw_types.items():
            if ifc_type.tag:
                if ifc_type.tag not in by_tag:
                    by_tag[ifc_type.tag] = []
                by_tag[ifc_type.tag].append(ifc_type)
            else:
                no_tag.append(ifc_type)
        
        # Consolidate each tag group - ONE entry per tag
        for tag, type_list in by_tag.items():
            # Use first as master, record all GUIDs
            master = type_list[0]
            master.consolidated_ids = [t.global_id for t in type_list]
            
            # Only add master to types dict (not all 27!)
            types[master.global_id] = master
            types_by_tag[tag] = master
        
        # Add types without tag
        for ifc_type in no_tag:
            types[ifc_type.global_id] = ifc_type
        
        return types, types_by_tag

    def _parse_elements(self, types: dict, types_by_tag: dict, errors: list):
        """Parse all building elements and aggregate quantities to types."""
        elements = {}
        elements_by_tag = {}
        
        for element_class in self.ELEMENT_TYPES:
            try:
                for ifc_element in self.ifc_file.by_type(element_class):
                    try:
                        parsed = self._parse_single_element(ifc_element, types, types_by_tag)
                        if parsed:
                            elements[parsed.global_id] = parsed
                            if parsed.tag:
                                elements_by_tag[parsed.tag] = parsed
                    except Exception as e:
                        errors.append(f"Error parsing {element_class}: {e}")
            except RuntimeError:
                continue
                
        return elements, elements_by_tag

    def _parse_single_element(self, ifc_element, types: dict, types_by_tag: dict) -> Optional[IFCElement]:
        """Parse a single IFC element and aggregate to its type."""
        global_id = ifc_element.GlobalId
        name = ifc_element.Name or ""
        tag = getattr(ifc_element, 'Tag', None)

        # Get type information
        type_id = None
        type_name = None
        family_name = None
        master_type = None

        try:
            element_type = element_util.get_type(ifc_element)
            if element_type:
                type_id = element_type.GlobalId
                type_name = element_type.Name
                type_tag = getattr(element_type, 'Tag', None)
                
                # Find the consolidated master type
                if type_tag and type_tag in types_by_tag:
                    master_type = types_by_tag[type_tag]
                elif type_id in types:
                    master_type = types[type_id]
                
                family_name, type_name = self._parse_type_name(type_name or name)
        except Exception:
            family_name, type_name = self._parse_type_name(name)

        # Get element quantities
        quantities = self._get_quantities(ifc_element)
        
        # Aggregate to master type
        if master_type:
            master_type.instance_count += 1
            for qty_name, qty_value in quantities.items():
                if qty_value is not None and isinstance(qty_value, (int, float)):
                    # Aggregate quantity value
                    if qty_name in master_type.quantities:
                        master_type.quantities[qty_name] += qty_value
                    else:
                        master_type.quantities[qty_name] = qty_value
                    # Track coverage: count how many instances have this quantity
                    if qty_name in master_type.quantity_coverage:
                        master_type.quantity_coverage[qty_name] += 1
                    else:
                        master_type.quantity_coverage[qty_name] = 1

        return IFCElement(
            global_id=global_id,
            tag=tag,
            name=name,
            ifc_class=ifc_element.is_a(),
            type_id=master_type.global_id if master_type else type_id,
            type_name=type_name,
            family_name=family_name,
            properties=self._get_properties(ifc_element),
            quantities=quantities,
            level=self._get_level(ifc_element)
        )

    def _parse_type_name(self, name: str) -> tuple:
        """Parse 'FamilyName:TypeName' into components."""
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
        except Exception:
            pass
        return properties

    def _get_property_value(self, prop):
        """Extract value from an IfcPropertySingleValue."""
        try:
            nominal_value = prop.NominalValue
            if nominal_value is None:
                return None
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