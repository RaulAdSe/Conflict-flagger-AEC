"""
Comparator module - Compares matched IFC types with BC3 elements.

FIXES IMPLEMENTED:
1. IFC=0 is WARNING, not ERROR (spaces, ceilings often have no quantities)
2. IfcSpace and IfcCovering are skipped (non-comparable)
3. Uses instance_count for unit quantities (u, ud, un)
4. Selects best area match (NetArea vs GrossArea) based on BC3 value
5. Code differences from name-matching are INFO, not ERROR
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum

# Import MatchMethod for comparison
try:
    from src.matching.matcher import MatchMethod
except ImportError:
    try:
        from matching.matcher import MatchMethod
    except ImportError:
        # Define locally if import fails
        class MatchMethod(Enum):
            BY_TAG = "Por Tag/ID"
            BY_GUID = "Por GUID"
            BY_NAME = "Por Nombre/Descripción"


class ConflictSeverity(Enum):
    ERROR = "ERROR"
    WARNING = "AVISO"
    INFO = "INFO"


class ConflictType(Enum):
    QUANTITY_MISMATCH = "Cantidad diferente"
    CODE_MISMATCH = "Código diferente"
    NAME_MISMATCH = "Nombre diferente"
    MISSING_IN_IFC = "Falta en IFC"
    MISSING_IN_BC3 = "Falta en BC3"


@dataclass
class Conflict:
    """A conflict/discrepancy found during comparison."""
    element_code: str
    element_name: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    property_name: str
    ifc_value: any
    bc3_value: any
    description: str
    quantity_source: str = ""  # What IFC quantity was used


@dataclass 
class ComparisonResult:
    """Result of comparing matched elements."""
    conflicts: List[Conflict] = field(default_factory=list)
    compared_count: int = 0
    
    def summary(self) -> dict:
        errors = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.ERROR)
        warnings = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.WARNING)
        infos = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.INFO)
        return {
            'total_conflicts': len(self.conflicts),
            'errors': errors,
            'warnings': warnings,
            'infos': infos,
            'compared': self.compared_count
        }


class Comparator:
    """
    Compares matched IFC-BC3 pairs and finds discrepancies.
    
    TOLERANCES:
    - Count units (u, ud): 0% (must be exact)
    - Areas (m²): 5% (Net vs Gross difference)
    - Volumes (m³): 5%
    - Lengths (m): 2%
    """
    
    # Families where automatic comparison may not be reliable
    NON_COMPARABLE_FAMILIES = [
        'System Panel',
        'Empty System Panel', 
        'Muro cortina',
        'Curtain Wall',
        'Curtain Panel',
    ]
    
    # IFC classes that often have no quantities
    NON_COMPARABLE_CLASSES = [
        'IfcSpace',       # Rooms/areas - often no area exported
        'IfcCovering',    # Ceilings - inconsistent quantities
    ]
    
    # Unit type mappings
    COUNT_UNITS = ['u', 'ud', 'un', 'pza', 'ut', 'unidad', 'uds', '']
    AREA_UNITS = ['m2', 'm²']
    VOLUME_UNITS = ['m3', 'm³']
    LENGTH_UNITS = ['m', 'ml']
    
    def __init__(self, tolerance: float = 0.05, compare_names: bool = True):
        """
        Initialize comparator.
        
        Args:
            tolerance: Default tolerance for quantity comparison (0.05 = 5%)
            compare_names: Whether to compare family/type names
        """
        self.tolerance = tolerance
        self.compare_names = compare_names
        
        # Specific tolerances by unit type
        self.tolerances = {
            'count': 0.0,    # Exact match for counts
            'area': 0.05,    # 5% for areas
            'volume': 0.05,  # 5% for volumes
            'length': 0.02,  # 2% for lengths
        }
    
    def compare(self, match_result, phase_config=None) -> ComparisonResult:
        """
        Compare all matched pairs and find conflicts.
        """
        result = ComparisonResult()
        
        for pair in match_result.matched:
            conflicts = self._compare_pair(pair)
            result.conflicts.extend(conflicts)
            result.compared_count += 1
        
        # Add warnings for unmatched elements
        for ifc_type in match_result.ifc_only:
            # Skip types with 0 instances
            if ifc_type.instance_count == 0:
                continue
            # Skip non-comparable classes
            if self._is_non_comparable_class(getattr(ifc_type, 'ifc_class', '')):
                continue
            result.conflicts.append(Conflict(
                element_code=ifc_type.tag or ifc_type.global_id[:8],
                element_name=ifc_type.name,
                conflict_type=ConflictType.MISSING_IN_BC3,
                severity=ConflictSeverity.WARNING,
                property_name="Presencia",
                ifc_value=f"{ifc_type.instance_count} instancias",
                bc3_value="-",
                description="Elemento en IFC pero no en presupuesto BC3"
            ))
        
        for bc3_elem in match_result.bc3_only:
            # Skip elements with 0 quantity
            if bc3_elem.quantity == 0:
                continue
            result.conflicts.append(Conflict(
                element_code=bc3_elem.code,
                element_name=bc3_elem.description,
                conflict_type=ConflictType.MISSING_IN_IFC,
                severity=ConflictSeverity.WARNING,
                property_name="Presencia",
                ifc_value="-",
                bc3_value=f"{bc3_elem.quantity} {bc3_elem.unit}",
                description="Elemento en BC3 pero no en modelo IFC"
            ))
        
        return result
    
    def _compare_pair(self, pair) -> List[Conflict]:
        """Compare a single matched pair."""
        conflicts = []
        ifc_type = pair.ifc_type
        bc3_elem = pair.bc3_element
        
        # 1. Compare codes (only if matched by name)
        if pair.match_method == MatchMethod.BY_NAME:
            ifc_code = ifc_type.tag or ifc_type.global_id[:8]
            if ifc_code != bc3_elem.code:
                # INFO, not ERROR - this is expected with Cost-It
                conflicts.append(Conflict(
                    element_code=bc3_elem.code,
                    element_name=bc3_elem.description,
                    conflict_type=ConflictType.CODE_MISMATCH,
                    severity=ConflictSeverity.INFO,  # Changed from ERROR
                    property_name="Código",
                    ifc_value=ifc_code,
                    bc3_value=bc3_elem.code,
                    description=f"Códigos diferentes (normal en Cost-It): IFC usa '{ifc_code}', BC3 usa '{bc3_elem.code}'"
                ))
        
        # 2. Compare quantities
        quantity_conflict = self._compare_quantities(ifc_type, bc3_elem)
        if quantity_conflict:
            conflicts.append(quantity_conflict)
        
        # 3. Compare names (if enabled)
        if self.compare_names:
            name_conflicts = self._compare_names(ifc_type, bc3_elem)
            conflicts.extend(name_conflicts)
        
        return conflicts
    
    def _compare_quantities(self, ifc_type, bc3_elem) -> Optional[Conflict]:
        """
        Compare quantities between IFC type and BC3 element.
        
        IMPORTANT: When IFC has 0 quantity, it's a WARNING not ERROR.
        This is common for IfcSpace, IfcCovering, etc.
        """
        bc3_unit = bc3_elem.unit.lower().strip()
        bc3_qty = bc3_elem.quantity
        
        # Skip if BC3 quantity is 0
        if bc3_qty == 0:
            return None
        
        # Check if this is a non-comparable family or class
        family_name = ifc_type.family_name or ifc_type.name or ""
        ifc_class = getattr(ifc_type, 'ifc_class', '')
        
        if self._is_non_comparable(family_name, ifc_class):
            # Don't report - these elements can't be compared automatically
            return None
        
        # Get IFC quantity based on BC3 unit
        ifc_qty, qty_source = self._get_ifc_quantity(ifc_type, bc3_unit, bc3_qty)
        
        # Determine tolerance based on unit type
        tolerance = self._get_tolerance_for_unit(bc3_unit)
        
        # Compare
        is_match, diff_pct = self._quantities_match(bc3_qty, ifc_qty, tolerance)
        
        if not is_match:
            # Determine severity based on the cause of mismatch
            if ifc_qty == 0:
                # No quantity at all in IFC
                severity = ConflictSeverity.WARNING
                description = f"Sin cantidad en IFC: BC3={bc3_qty:.2f} {bc3_elem.unit}, IFC no exporta {qty_source}"
            else:
                # Check if this is due to incomplete IFC export
                # (some instances missing the quantity)
                is_incomplete_export = self._is_incomplete_export(ifc_type, qty_source)

                if is_incomplete_export:
                    # Some instances don't have this quantity exported
                    severity = ConflictSeverity.WARNING
                    coverage = getattr(ifc_type, 'quantity_coverage', {})
                    instances_with_qty = coverage.get(qty_source, 0)
                    instances_without = ifc_type.instance_count - instances_with_qty
                    description = (f"Exportación IFC incompleta: BC3={bc3_qty:.2f} {bc3_elem.unit}, "
                                   f"IFC={ifc_qty:.2f} ({qty_source}) - {instances_without} de "
                                   f"{ifc_type.instance_count} instancias sin {qty_source}")
                elif self._is_length_export_bug(ifc_type, qty_source, ifc_qty):
                    # MappedRepresentation beam with incorrect Length quantity
                    severity = ConflictSeverity.WARNING
                    net_vol = ifc_type.quantities.get('NetVolume', 0)
                    description = (f"Exportación IFC incorrecta (MappedRepresentation): "
                                   f"BC3={bc3_qty:.2f} {bc3_elem.unit}, IFC Length={ifc_qty:.2f} "
                                   f"(NetVolume={net_vol:.2f}m³ sugiere longitud mayor)")
                else:
                    # All instances have the quantity, but values differ - real error
                    severity = ConflictSeverity.ERROR
                    description = f"Cantidad difiere: BC3={bc3_qty:.2f} {bc3_elem.unit}, IFC={ifc_qty:.2f} ({qty_source}) - {diff_pct*100:.1f}%"

            return Conflict(
                element_code=bc3_elem.code,
                element_name=bc3_elem.description,
                conflict_type=ConflictType.QUANTITY_MISMATCH,
                severity=severity,
                property_name="Cantidad",
                ifc_value=round(ifc_qty, 2),
                bc3_value=round(bc3_qty, 2),
                description=description,
                quantity_source=qty_source
            )
        
        return None
    
    def _get_ifc_quantity(self, ifc_type, bc3_unit: str, bc3_qty: float) -> Tuple[float, str]:
        """
        Get the appropriate IFC quantity based on BC3 unit.
        
        Returns:
            Tuple of (quantity_value, quantity_source_name)
        """
        # COUNT UNITS → instance_count
        if bc3_unit in self.COUNT_UNITS:
            return ifc_type.instance_count, "instancias"
        
        # AREA UNITS → select best match
        if bc3_unit in self.AREA_UNITS:
            return self._get_best_area(ifc_type, bc3_qty)
        
        # VOLUME UNITS - select best match (closest to BC3)
        if bc3_unit in self.VOLUME_UNITS:
            return self._get_best_volume(ifc_type, bc3_qty)
        
        # LENGTH UNITS
        if bc3_unit in self.LENGTH_UNITS:
            length = ifc_type.quantities.get('Length', 0)
            if length > 0:
                return length, "Length"
            return 0, "NoLength"
        
        # DEFAULT → instance_count
        return ifc_type.instance_count, "instancias"
    
    def _get_best_area(self, ifc_type, bc3_qty: float) -> Tuple[float, str]:
        """
        Select the IFC area that best matches the BC3 quantity.

        Candidates: NetArea, GrossArea, GrossSideArea, NetSideArea
        """
        candidates = [
            (ifc_type.quantities.get('NetArea', 0), 'NetArea'),
            (ifc_type.quantities.get('GrossArea', 0), 'GrossArea'),
            (ifc_type.quantities.get('GrossSideArea', 0), 'GrossSideArea'),
            (ifc_type.quantities.get('NetSideArea', 0), 'NetSideArea'),
        ]

        # Filter out zeros
        valid = [(v, n) for v, n in candidates if v > 0]

        if not valid:
            return 0, "NoArea"

        if bc3_qty <= 0:
            # Default to first available
            return valid[0]

        # Find closest to BC3 quantity
        best = min(valid, key=lambda x: abs(x[0] - bc3_qty))
        return best

    def _get_best_volume(self, ifc_type, bc3_qty: float) -> Tuple[float, str]:
        """
        Select the IFC volume that best matches the BC3 quantity.

        Since BC3 was generated from IFC via CostIt, we should match
        whichever volume CostIt chose to use. This is determined by
        finding the closest match to the BC3 value.

        Candidates: NetVolume, GrossVolume
        """
        candidates = [
            (ifc_type.quantities.get('NetVolume', 0), 'NetVolume'),
            (ifc_type.quantities.get('GrossVolume', 0), 'GrossVolume'),
        ]

        # Filter out zeros
        valid = [(v, n) for v, n in candidates if v > 0]

        if not valid:
            return 0, "NoVolume"

        if bc3_qty <= 0:
            # Default to first available
            return valid[0]

        # Find closest to BC3 quantity (match CostIt's choice)
        best = min(valid, key=lambda x: abs(x[0] - bc3_qty))
        return best
    
    def _get_tolerance_for_unit(self, bc3_unit: str) -> float:
        """Get the appropriate tolerance based on unit type."""
        if bc3_unit in self.COUNT_UNITS:
            return self.tolerances['count']
        if bc3_unit in self.AREA_UNITS:
            return self.tolerances['area']
        if bc3_unit in self.VOLUME_UNITS:
            return self.tolerances['volume']
        if bc3_unit in self.LENGTH_UNITS:
            return self.tolerances['length']
        return self.tolerance
    
    def _quantities_match(self, bc3_qty: float, ifc_qty: float, tolerance: float) -> Tuple[bool, float]:
        """
        Check if quantities match within tolerance.
        
        Returns:
            Tuple of (is_match, difference_percentage)
        """
        if bc3_qty == 0 and ifc_qty == 0:
            return True, 0.0
        
        if bc3_qty == 0 or ifc_qty == 0:
            return False, 1.0
        
        diff_pct = abs(bc3_qty - ifc_qty) / max(bc3_qty, ifc_qty)
        
        return diff_pct <= tolerance, diff_pct
    
    def _is_non_comparable(self, family_name: str, ifc_class: str = "") -> bool:
        """Check if family or IFC class is in the non-comparable list."""
        # Check family name
        family_lower = family_name.lower()
        for nc in self.NON_COMPARABLE_FAMILIES:
            if nc.lower() in family_lower:
                return True
        
        # Check IFC class
        return self._is_non_comparable_class(ifc_class)
    
    def _is_non_comparable_class(self, ifc_class: str) -> bool:
        """Check if IFC class is non-comparable."""
        if not ifc_class:
            return False
        ifc_class_lower = ifc_class.lower()
        for nc_class in self.NON_COMPARABLE_CLASSES:
            if nc_class.lower() in ifc_class_lower:
                return True
        return False
    
    def _compare_names(self, ifc_type, bc3_elem) -> List[Conflict]:
        """Compare family and type names."""
        conflicts = []
        
        # Compare family name
        ifc_family = ifc_type.family_name or ""
        bc3_family = bc3_elem.family_name or ""
        
        if ifc_family and bc3_family:
            if self._normalize(ifc_family) != self._normalize(bc3_family):
                conflicts.append(Conflict(
                    element_code=bc3_elem.code,
                    element_name=bc3_elem.description,
                    conflict_type=ConflictType.NAME_MISMATCH,
                    severity=ConflictSeverity.INFO,  # INFO, not WARNING
                    property_name="Family Name",
                    ifc_value=ifc_family,
                    bc3_value=bc3_family,
                    description="Family name differs"
                ))
        
        # Compare type name
        ifc_type_name = ifc_type.type_name or ""
        bc3_type_name = bc3_elem.type_name or ""
        
        if ifc_type_name and bc3_type_name:
            if self._normalize(ifc_type_name) != self._normalize(bc3_type_name):
                conflicts.append(Conflict(
                    element_code=bc3_elem.code,
                    element_name=bc3_elem.description,
                    conflict_type=ConflictType.NAME_MISMATCH,
                    severity=ConflictSeverity.INFO,
                    property_name="Type Name",
                    ifc_value=ifc_type_name,
                    bc3_value=bc3_type_name,
                    description="Type name differs"
                ))
        
        return conflicts

    def _is_incomplete_export(self, ifc_type, qty_source: str) -> bool:
        """
        Check if the IFC export is incomplete for a given quantity.

        Returns True if some instances are missing the quantity (incomplete export).
        Returns False if all instances have the quantity (complete export, real discrepancy).
        """
        # Get quantity coverage info
        coverage = getattr(ifc_type, 'quantity_coverage', {})

        # If no coverage info available, assume complete export
        if not coverage:
            return False

        # For count-based quantities (instancias), coverage doesn't apply
        if qty_source == "instancias":
            return False

        # Get how many instances have this quantity
        instances_with_qty = coverage.get(qty_source, 0)
        total_instances = ifc_type.instance_count

        # If all instances have the quantity, it's a complete export
        if instances_with_qty >= total_instances:
            return False

        # Some instances are missing the quantity - incomplete export
        return instances_with_qty < total_instances and instances_with_qty > 0

    def _is_length_export_bug(self, ifc_type, qty_source: str, ifc_qty: float) -> bool:
        """
        Detect export bugs where Length quantity is incorrect but Volume is valid.

        Some elements exported with MappedRepresentation geometry have their Length
        quantity incorrectly set (e.g., to a clipping operation depth ~0.25m)
        rather than the actual element length. However, NetVolume is often
        correctly calculated from actual geometry.

        This applies to linear elements (beams, columns, structural members).

        Returns True if this appears to be such an export bug.
        """
        # Only applies to Length comparisons
        if qty_source != "Length":
            return False

        # Only applies to linear elements (beams, columns, members)
        ifc_class = getattr(ifc_type, 'ifc_class', '').lower()
        linear_classes = ['beam', 'column', 'member', 'pile']
        if not any(cls in ifc_class for cls in linear_classes):
            return False

        # Check if Length is suspiciously small (typical clipping depth is ~0.25-0.5m)
        if ifc_qty > 0.5:
            return False

        # Check if NetVolume is much larger than would be expected for this Length
        net_vol = ifc_type.quantities.get('NetVolume', 0)
        if net_vol <= 0:
            return False

        # For an element with Length=0.25m and reasonable cross-section (up to 1.5m²),
        # expected volume would be at most 0.375m³
        # If NetVolume is much larger, Length is likely wrong
        expected_max_vol_for_length = ifc_qty * 1.5  # Max cross section 1.5m²
        if net_vol > expected_max_vol_for_length * 2:
            # NetVolume suggests element is much longer than reported Length
            return True

        return False

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip().replace('_', ' ').replace('-', ' ')