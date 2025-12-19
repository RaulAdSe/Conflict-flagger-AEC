"""
Comparator for finding differences between matched IFC and BC3 elements.

Compares properties, quantities, and metadata to flag discrepancies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.matching.matcher import MatchedPair, MatchResult, MatchStatus


class ConflictType(Enum):
    """Type of conflict detected."""
    MISSING_IN_BC3 = "missing_in_bc3"  # Element only in IFC
    MISSING_IN_IFC = "missing_in_ifc"  # Element only in BC3
    PROPERTY_MISMATCH = "property_mismatch"  # Different property values
    PROPERTY_MISSING_IFC = "property_missing_ifc"  # Property only in BC3
    PROPERTY_MISSING_BC3 = "property_missing_bc3"  # Property only in IFC
    NAME_MISMATCH = "name_mismatch"  # Family/Type name differs
    QUANTITY_MISMATCH = "quantity_mismatch"  # Quantity values differ


class ConflictSeverity(Enum):
    """Severity of the conflict."""
    ERROR = "error"  # Red - Values are different
    WARNING = "warning"  # Yellow - Missing data
    INFO = "info"  # Blue - Informational


@dataclass
class Conflict:
    """Represents a single conflict/difference."""

    conflict_type: ConflictType
    severity: ConflictSeverity

    # Element identification
    code: Optional[str]
    element_name: str

    # Conflict details
    property_name: Optional[str] = None
    ifc_value: Any = None
    bc3_value: Any = None

    # Context
    message: str = ""

    def __str__(self) -> str:
        if self.property_name:
            return f"[{self.severity.value.upper()}] {self.code}: {self.property_name} - IFC: {self.ifc_value}, BC3: {self.bc3_value}"
        return f"[{self.severity.value.upper()}] {self.code}: {self.message}"


@dataclass
class ComparisonResult:
    """Result of comparing matched pairs."""

    conflicts: list  # List of Conflict objects

    # Counts by type
    missing_in_bc3: int = 0
    missing_in_ifc: int = 0
    property_mismatches: int = 0
    total_properties_compared: int = 0

    # Summary
    total_matched: int = 0
    total_with_conflicts: int = 0

    errors: list = field(default_factory=list)

    def get_conflicts_by_type(self, conflict_type: ConflictType) -> list[Conflict]:
        """Get all conflicts of a specific type."""
        return [c for c in self.conflicts if c.conflict_type == conflict_type]

    def get_conflicts_by_severity(self, severity: ConflictSeverity) -> list[Conflict]:
        """Get all conflicts of a specific severity."""
        return [c for c in self.conflicts if c.severity == severity]

    def get_conflicts_for_code(self, code: str) -> list[Conflict]:
        """Get all conflicts for a specific element code."""
        return [c for c in self.conflicts if c.code == code]

    def summary(self) -> dict:
        """Get a summary of the comparison results."""
        return {
            "total_conflicts": len(self.conflicts),
            "errors": len(self.get_conflicts_by_severity(ConflictSeverity.ERROR)),
            "warnings": len(self.get_conflicts_by_severity(ConflictSeverity.WARNING)),
            "missing_in_bc3": self.missing_in_bc3,
            "missing_in_ifc": self.missing_in_ifc,
            "property_mismatches": self.property_mismatches,
            "total_matched": self.total_matched,
            "total_with_conflicts": self.total_with_conflicts
        }


class Comparator:
    """Compares matched IFC and BC3 elements to find differences."""

    # Properties to compare between IFC and BC3
    COMPARABLE_PROPERTIES = [
        # Dimensional
        ('h', 'h'),
        ('b', 'b'),
        ('Anchura', 'width'),
        ('Altura', 'height'),
        ('Grosor', 'thickness'),
        ('Longitud', 'length'),
        # Material
        ('Material', 'Material'),
        ('Material estructural', 'StructuralMaterial'),
        # Thermal
        ('Resistencia térmica (R)', 'ThermalResistance'),
        ('Coeficiente de transferencia de calor (U)', 'HeatTransferCoefficient'),
    ]

    def __init__(self, tolerance: float = 0.01, compare_names: bool = True):
        """
        Initialize the comparator.

        Args:
            tolerance: Numeric tolerance for value comparison
            compare_names: Whether to compare family/type names
        """
        self.tolerance = tolerance
        self.compare_names = compare_names

    def compare(self, match_result: MatchResult) -> ComparisonResult:
        """
        Compare all matched pairs and find conflicts.

        Args:
            match_result: Result from the Matcher

        Returns:
            ComparisonResult with all conflicts found
        """
        conflicts = []
        errors = []
        codes_with_conflicts = set()

        # Report missing items
        for pair in match_result.ifc_only:
            conflict = Conflict(
                conflict_type=ConflictType.MISSING_IN_BC3,
                severity=ConflictSeverity.WARNING,
                code=pair.code,
                element_name=pair.name,
                message=f"Element exists in IFC but not in BC3 budget"
            )
            conflicts.append(conflict)
            if pair.code:
                codes_with_conflicts.add(pair.code)

        for pair in match_result.bc3_only:
            conflict = Conflict(
                conflict_type=ConflictType.MISSING_IN_IFC,
                severity=ConflictSeverity.WARNING,
                code=pair.code,
                element_name=pair.name,
                message=f"Element exists in BC3 but not in IFC model"
            )
            conflicts.append(conflict)
            if pair.code:
                codes_with_conflicts.add(pair.code)

        # Compare matched pairs
        total_props_compared = 0
        for pair in match_result.matched:
            try:
                pair_conflicts, props_compared = self._compare_pair(pair)
                conflicts.extend(pair_conflicts)
                total_props_compared += props_compared

                if pair_conflicts and pair.code:
                    codes_with_conflicts.add(pair.code)
            except Exception as e:
                errors.append(f"Error comparing {pair.code}: {e}")

        return ComparisonResult(
            conflicts=conflicts,
            missing_in_bc3=len(match_result.ifc_only),
            missing_in_ifc=len(match_result.bc3_only),
            property_mismatches=len([c for c in conflicts
                                    if c.conflict_type == ConflictType.PROPERTY_MISMATCH]),
            total_properties_compared=total_props_compared,
            total_matched=len(match_result.matched),
            total_with_conflicts=len(codes_with_conflicts),
            errors=errors
        )

    def _compare_pair(self, pair: MatchedPair) -> tuple[list[Conflict], int]:
        """
        Compare a single matched pair.

        Returns:
            Tuple of (list of conflicts, number of properties compared)
        """
        conflicts = []
        props_compared = 0

        if not pair.bc3_element or not pair.ifc_type:
            return conflicts, props_compared

        bc3 = pair.bc3_element
        ifc = pair.ifc_type

        # Compare names if enabled
        if self.compare_names:
            name_conflicts = self._compare_names(pair)
            conflicts.extend(name_conflicts)

        # Compare properties
        bc3_props = bc3.properties or {}
        ifc_props = ifc.properties or {}

        # Check known comparable properties
        for bc3_key, ifc_key in self.COMPARABLE_PROPERTIES:
            bc3_val = bc3_props.get(bc3_key)
            ifc_val = ifc_props.get(ifc_key)

            if bc3_val is None and ifc_val is None:
                continue

            props_compared += 1

            if bc3_val is None:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.PROPERTY_MISSING_BC3,
                    severity=ConflictSeverity.INFO,
                    code=pair.code,
                    element_name=pair.name,
                    property_name=bc3_key,
                    ifc_value=ifc_val,
                    bc3_value=None,
                    message=f"Property '{bc3_key}' exists in IFC but not in BC3"
                ))
            elif ifc_val is None:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.PROPERTY_MISSING_IFC,
                    severity=ConflictSeverity.INFO,
                    code=pair.code,
                    element_name=pair.name,
                    property_name=bc3_key,
                    ifc_value=None,
                    bc3_value=bc3_val,
                    message=f"Property '{bc3_key}' exists in BC3 but not in IFC"
                ))
            elif not self._values_equal(bc3_val, ifc_val):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.PROPERTY_MISMATCH,
                    severity=ConflictSeverity.ERROR,
                    code=pair.code,
                    element_name=pair.name,
                    property_name=bc3_key,
                    ifc_value=ifc_val,
                    bc3_value=bc3_val,
                    message=f"Property '{bc3_key}' differs: IFC={ifc_val}, BC3={bc3_val}"
                ))

        # Also compare any BC3 properties that have same name as IFC properties
        for key, bc3_val in bc3_props.items():
            if key in ifc_props:
                ifc_val = ifc_props[key]
                # Skip if already compared via COMPARABLE_PROPERTIES
                if any(bc3_key == key for bc3_key, _ in self.COMPARABLE_PROPERTIES):
                    continue

                props_compared += 1

                if not self._values_equal(bc3_val, ifc_val):
                    conflicts.append(Conflict(
                        conflict_type=ConflictType.PROPERTY_MISMATCH,
                        severity=ConflictSeverity.ERROR,
                        code=pair.code,
                        element_name=pair.name,
                        property_name=key,
                        ifc_value=ifc_val,
                        bc3_value=bc3_val,
                        message=f"Property '{key}' differs: IFC={ifc_val}, BC3={bc3_val}"
                    ))

        return conflicts, props_compared

    def _compare_names(self, pair: MatchedPair) -> list[Conflict]:
        """Compare family and type names."""
        conflicts = []

        if not pair.bc3_element or not pair.ifc_type:
            return conflicts

        bc3 = pair.bc3_element
        ifc = pair.ifc_type

        # Compare family names
        if bc3.family_name and ifc.family_name:
            if not self._strings_similar(bc3.family_name, ifc.family_name):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.NAME_MISMATCH,
                    severity=ConflictSeverity.WARNING,
                    code=pair.code,
                    element_name=pair.name,
                    property_name="Family Name",
                    ifc_value=ifc.family_name,
                    bc3_value=bc3.family_name,
                    message=f"Family name differs"
                ))

        # Compare type names
        if bc3.type_name and ifc.type_name:
            if not self._strings_similar(bc3.type_name, ifc.type_name):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.NAME_MISMATCH,
                    severity=ConflictSeverity.WARNING,
                    code=pair.code,
                    element_name=pair.name,
                    property_name="Type Name",
                    ifc_value=ifc.type_name,
                    bc3_value=bc3.type_name,
                    message=f"Type name differs"
                ))

        return conflicts

    def _values_equal(self, val1: Any, val2: Any) -> bool:
        """
        Compare two values with tolerance for numeric values.

        Args:
            val1: First value
            val2: Second value

        Returns:
            True if values are considered equal
        """
        # Handle None
        if val1 is None and val2 is None:
            return True
        if val1 is None or val2 is None:
            return False

        # Try numeric comparison
        try:
            num1 = float(val1)
            num2 = float(val2)
            return abs(num1 - num2) <= self.tolerance
        except (ValueError, TypeError):
            pass

        # String comparison (case-insensitive)
        str1 = str(val1).strip().lower()
        str2 = str(val2).strip().lower()
        return str1 == str2

    def _strings_similar(self, s1: str, s2: str) -> bool:
        """
        Check if two strings are similar (case-insensitive, whitespace-normalized).
        """
        if not s1 or not s2:
            return False

        # Normalize
        n1 = ' '.join(s1.lower().split())
        n2 = ' '.join(s2.lower().split())

        return n1 == n2

    def get_error_conflicts(self, result: ComparisonResult) -> list[Conflict]:
        """Get all ERROR severity conflicts."""
        return result.get_conflicts_by_severity(ConflictSeverity.ERROR)

    def get_warning_conflicts(self, result: ComparisonResult) -> list[Conflict]:
        """Get all WARNING severity conflicts."""
        return result.get_conflicts_by_severity(ConflictSeverity.WARNING)
