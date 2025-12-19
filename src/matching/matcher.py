"""
Matcher for linking IFC elements to BC3 elements.

Uses multiple strategies for robust matching:
1. Primary: Tag (Revit Element ID) ↔ BC3 Code
2. Secondary: IFC GlobalId ↔ BC3 Tipo IfcGUID
3. Fallback: Family + Type name matching
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.parsers.bc3_parser import BC3Element, BC3ParseResult
from src.parsers.ifc_parser import IFCElement, IFCType, IFCParseResult


class MatchMethod(Enum):
    """How the match was determined."""
    TAG = "tag"  # Matched via Tag ↔ Code
    GUID = "guid"  # Matched via GlobalId ↔ Tipo IfcGUID
    NAME = "name"  # Matched via family/type name similarity
    NONE = "none"  # No match found


class MatchStatus(Enum):
    """Status of the match."""
    MATCHED = "matched"  # Found in both sources
    IFC_ONLY = "ifc_only"  # Only in IFC (missing from BC3)
    BC3_ONLY = "bc3_only"  # Only in BC3 (missing from IFC)


@dataclass
class MatchedPair:
    """A matched pair of IFC and BC3 elements."""

    status: MatchStatus
    method: MatchMethod

    # IFC side (may be None if BC3_ONLY)
    ifc_element: Optional[IFCElement] = None
    ifc_type: Optional[IFCType] = None

    # BC3 side (may be None if IFC_ONLY)
    bc3_element: Optional[BC3Element] = None

    # Matching key used
    match_key: Optional[str] = None

    # Confidence score (0-1)
    confidence: float = 1.0

    @property
    def code(self) -> Optional[str]:
        """Get the primary code/identifier."""
        if self.bc3_element:
            return self.bc3_element.code
        if self.ifc_type and self.ifc_type.tag:
            return self.ifc_type.tag
        if self.ifc_element and self.ifc_element.tag:
            return self.ifc_element.tag
        return None

    @property
    def name(self) -> str:
        """Get a descriptive name."""
        if self.bc3_element:
            return self.bc3_element.description
        if self.ifc_type:
            return self.ifc_type.name
        if self.ifc_element:
            return self.ifc_element.name
        return "Unknown"


@dataclass
class MatchResult:
    """Result of matching IFC and BC3 data."""

    matched: list  # List of MatchedPair with status=MATCHED
    ifc_only: list  # List of MatchedPair with status=IFC_ONLY
    bc3_only: list  # List of MatchedPair with status=BC3_ONLY

    # Statistics
    total_ifc_types: int = 0
    total_bc3_elements: int = 0
    match_count: int = 0

    # Errors during matching
    errors: list = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        """Calculate the match rate as a percentage."""
        total = self.total_ifc_types + self.total_bc3_elements
        if total == 0:
            return 0.0
        # Each match covers 2 items (one from each side)
        return (self.match_count * 2 / total) * 100

    def summary(self) -> dict:
        """Get a summary of the match results."""
        return {
            "total_ifc_types": self.total_ifc_types,
            "total_bc3_elements": self.total_bc3_elements,
            "matched": len(self.matched),
            "ifc_only": len(self.ifc_only),
            "bc3_only": len(self.bc3_only),
            "match_rate": f"{self.match_rate:.1f}%"
        }


class Matcher:
    """Matches IFC elements with BC3 elements."""

    def __init__(self, match_by_name: bool = True):
        """
        Initialize the matcher.

        Args:
            match_by_name: Whether to attempt name-based matching as fallback
        """
        self.match_by_name = match_by_name

    def match(self, ifc_result: IFCParseResult, bc3_result: BC3ParseResult) -> MatchResult:
        """
        Match IFC types with BC3 elements.

        The matching is done at the TYPE level, not instance level,
        since BC3 typically contains type definitions with quantities.

        Args:
            ifc_result: Parsed IFC data
            bc3_result: Parsed BC3 data

        Returns:
            MatchResult with matched pairs and unmatched items
        """
        matched = []
        ifc_only = []
        bc3_only = []
        errors = []

        # Track what's been matched
        matched_ifc_ids = set()
        matched_bc3_codes = set()

        # Get BC3 elements with IFC GUIDs for GUID matching
        bc3_by_guid = {
            elem.type_ifc_guid: elem
            for elem in bc3_result.elements.values()
            if elem.type_ifc_guid
        }

        # Strategy 1: Match by Tag ↔ Code
        for tag, ifc_type in ifc_result.types_by_tag.items():
            if tag in bc3_result.elements:
                bc3_elem = bc3_result.elements[tag]
                pair = MatchedPair(
                    status=MatchStatus.MATCHED,
                    method=MatchMethod.TAG,
                    ifc_type=ifc_type,
                    bc3_element=bc3_elem,
                    match_key=tag,
                    confidence=1.0
                )
                matched.append(pair)
                matched_ifc_ids.add(ifc_type.global_id)
                matched_bc3_codes.add(tag)

        # Strategy 2: Match by GlobalId ↔ Tipo IfcGUID
        for guid, ifc_type in ifc_result.types.items():
            if guid in matched_ifc_ids:
                continue

            if guid in bc3_by_guid:
                bc3_elem = bc3_by_guid[guid]
                if bc3_elem.code not in matched_bc3_codes:
                    pair = MatchedPair(
                        status=MatchStatus.MATCHED,
                        method=MatchMethod.GUID,
                        ifc_type=ifc_type,
                        bc3_element=bc3_elem,
                        match_key=guid,
                        confidence=1.0
                    )
                    matched.append(pair)
                    matched_ifc_ids.add(guid)
                    matched_bc3_codes.add(bc3_elem.code)

        # Strategy 3: Match by name (optional, lower confidence)
        if self.match_by_name:
            self._match_by_name(
                ifc_result, bc3_result,
                matched_ifc_ids, matched_bc3_codes,
                matched
            )

        # Collect unmatched IFC types
        for guid, ifc_type in ifc_result.types.items():
            if guid not in matched_ifc_ids:
                pair = MatchedPair(
                    status=MatchStatus.IFC_ONLY,
                    method=MatchMethod.NONE,
                    ifc_type=ifc_type
                )
                ifc_only.append(pair)

        # Collect unmatched BC3 elements (only those with properties, not hierarchy nodes)
        for code, bc3_elem in bc3_result.elements.items():
            if code not in matched_bc3_codes:
                # Skip hierarchy-only elements (those ending with # in original)
                # and elements without meaningful data
                if bc3_elem.unit or bc3_elem.type_ifc_guid or bc3_elem.properties:
                    pair = MatchedPair(
                        status=MatchStatus.BC3_ONLY,
                        method=MatchMethod.NONE,
                        bc3_element=bc3_elem
                    )
                    bc3_only.append(pair)

        return MatchResult(
            matched=matched,
            ifc_only=ifc_only,
            bc3_only=bc3_only,
            total_ifc_types=len(ifc_result.types),
            total_bc3_elements=len([e for e in bc3_result.elements.values()
                                   if e.unit or e.type_ifc_guid or e.properties]),
            match_count=len(matched),
            errors=errors
        )

    def _match_by_name(
        self,
        ifc_result: IFCParseResult,
        bc3_result: BC3ParseResult,
        matched_ifc_ids: set,
        matched_bc3_codes: set,
        matched: list
    ) -> None:
        """
        Attempt to match remaining items by family/type name.

        This is a fallback strategy with lower confidence.
        """
        # Build name index for BC3
        bc3_by_name = {}
        for code, elem in bc3_result.elements.items():
            if code in matched_bc3_codes:
                continue
            if elem.family_name and elem.type_name:
                key = f"{elem.family_name}:{elem.type_name}".lower()
                bc3_by_name[key] = elem

        # Try to match unmatched IFC types
        for guid, ifc_type in ifc_result.types.items():
            if guid in matched_ifc_ids:
                continue

            # Build search key from IFC type
            if ifc_type.family_name and ifc_type.type_name:
                key = f"{ifc_type.family_name}:{ifc_type.type_name}".lower()
            elif ifc_type.name:
                key = ifc_type.name.lower()
            else:
                continue

            # Look for exact match
            if key in bc3_by_name:
                bc3_elem = bc3_by_name[key]
                if bc3_elem.code not in matched_bc3_codes:
                    pair = MatchedPair(
                        status=MatchStatus.MATCHED,
                        method=MatchMethod.NAME,
                        ifc_type=ifc_type,
                        bc3_element=bc3_elem,
                        match_key=key,
                        confidence=0.8  # Lower confidence for name matching
                    )
                    matched.append(pair)
                    matched_ifc_ids.add(guid)
                    matched_bc3_codes.add(bc3_elem.code)

    def get_matched_by_method(self, result: MatchResult, method: MatchMethod) -> list[MatchedPair]:
        """Get all matches that used a specific method."""
        return [m for m in result.matched if m.method == method]

    def get_high_confidence_matches(self, result: MatchResult, threshold: float = 0.9) -> list[MatchedPair]:
        """Get matches above a confidence threshold."""
        return [m for m in result.matched if m.confidence >= threshold]
