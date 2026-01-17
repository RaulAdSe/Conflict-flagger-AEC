"""Tests for Comparator."""

import pytest
from pathlib import Path

from src.parsers.bc3_parser import BC3Element
from src.parsers.ifc_parser import IFCType
from src.matching.matcher import MatchedPair, MatchResult, MatchStatus, MatchMethod
from src.comparison.comparator import (
    Comparator, Conflict, ConflictType, ConflictSeverity, ComparisonResult
)


class TestConflict:
    """Tests for Conflict dataclass."""

    def test_create_conflict(self):
        """Test creating a conflict."""
        conflict = Conflict(
            conflict_type=ConflictType.PROPERTY_MISMATCH,
            severity=ConflictSeverity.ERROR,
            code="350147",
            element_name="Column",
            property_name="height",
            ifc_value=2.5,
            bc3_value=2.6,
            message="Height differs"
        )

        assert conflict.conflict_type == ConflictType.PROPERTY_MISMATCH
        assert conflict.severity == ConflictSeverity.ERROR
        assert conflict.code == "350147"
        assert conflict.property_name == "height"

    def test_conflict_string(self):
        """Test conflict string representation."""
        conflict = Conflict(
            conflict_type=ConflictType.PROPERTY_MISMATCH,
            severity=ConflictSeverity.ERROR,
            code="350147",
            element_name="Column",
            property_name="h",
            ifc_value=0.6,
            bc3_value=0.8
        )

        s = str(conflict)
        assert "ERROR" in s
        assert "350147" in s
        assert "h" in s


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_get_conflicts_by_type(self):
        """Test filtering conflicts by type."""
        conflicts = [
            Conflict(
                conflict_type=ConflictType.MISSING_IN_BC3,
                severity=ConflictSeverity.WARNING,
                code="1",
                element_name="A"
            ),
            Conflict(
                conflict_type=ConflictType.PROPERTY_MISMATCH,
                severity=ConflictSeverity.ERROR,
                code="2",
                element_name="B"
            ),
            Conflict(
                conflict_type=ConflictType.MISSING_IN_BC3,
                severity=ConflictSeverity.WARNING,
                code="3",
                element_name="C"
            ),
        ]

        result = ComparisonResult(conflicts=conflicts)

        missing = result.get_conflicts_by_type(ConflictType.MISSING_IN_BC3)
        assert len(missing) == 2

        mismatches = result.get_conflicts_by_type(ConflictType.PROPERTY_MISMATCH)
        assert len(mismatches) == 1

    def test_get_conflicts_by_severity(self):
        """Test filtering conflicts by severity."""
        conflicts = [
            Conflict(
                conflict_type=ConflictType.MISSING_IN_BC3,
                severity=ConflictSeverity.WARNING,
                code="1",
                element_name="A"
            ),
            Conflict(
                conflict_type=ConflictType.PROPERTY_MISMATCH,
                severity=ConflictSeverity.ERROR,
                code="2",
                element_name="B"
            ),
        ]

        result = ComparisonResult(conflicts=conflicts)

        errors = result.get_conflicts_by_severity(ConflictSeverity.ERROR)
        assert len(errors) == 1

        warnings = result.get_conflicts_by_severity(ConflictSeverity.WARNING)
        assert len(warnings) == 1

    def test_summary(self):
        """Test summary generation."""
        conflicts = [
            Conflict(ConflictType.MISSING_IN_BC3, ConflictSeverity.WARNING, "1", "A"),
            Conflict(ConflictType.PROPERTY_MISMATCH, ConflictSeverity.ERROR, "2", "B"),
            Conflict(ConflictType.MISSING_IN_IFC, ConflictSeverity.WARNING, "3", "C"),
        ]
        result = ComparisonResult(
            conflicts=conflicts,
            missing_in_bc3=2,
            missing_in_ifc=1,
            property_mismatches=5,
            total_matched=10
        )

        summary = result.summary()
        assert summary["total_conflicts"] == 3
        assert summary["missing_in_bc3"] == 2
        assert summary["missing_in_ifc"] == 1
        assert summary["errors"] == 1
        assert summary["warnings"] == 2


class TestComparator:
    """Tests for Comparator class."""

    @pytest.fixture
    def comparator(self):
        """Create a comparator instance."""
        return Comparator(tolerance=0.01)

    @pytest.fixture
    def matched_pair_with_differences(self):
        """Create a matched pair with property differences."""
        bc3 = BC3Element(
            code="350147",
            unit="m3",
            description="Column 600x600",
            price=150.0,
            family_name="Pilar",
            type_name="600x600",
            properties={"h": 0.6, "b": 0.6, "Material": "Concrete"}
        )

        ifc = IFCType(
            global_id="guid1",
            tag="350147",
            name="Pilar:600x600",
            ifc_class="IfcColumnType",
            family_name="Pilar",
            type_name="600x600",
            properties={"h": 0.8, "b": 0.6, "Material": "Steel"}  # h and Material differ
        )

        return MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc,
            bc3_element=bc3,
            match_key="350147"
        )

    @pytest.fixture
    def matched_pair_identical(self):
        """Create a matched pair with identical properties."""
        bc3 = BC3Element(
            code="352900",
            unit="m",
            description="Beam I-220",
            price=200.0,
            family_name="Jácena",
            type_name="I-220",
            properties={"h": 1.2, "b": 0.4}
        )

        ifc = IFCType(
            global_id="guid2",
            tag="352900",
            name="Jácena:I-220",
            ifc_class="IfcBeamType",
            family_name="Jácena",
            type_name="I-220",
            properties={"h": 1.2, "b": 0.4}
        )

        return MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc,
            bc3_element=bc3,
            match_key="352900"
        )

    @pytest.fixture
    def ifc_only_pair(self):
        """Create an IFC-only pair."""
        ifc = IFCType(
            global_id="guid3",
            tag="999",
            name="Unbudgeted:Type",
            ifc_class="IfcWallType"
        )

        return MatchedPair(
            status=MatchStatus.IFC_ONLY,
            method=MatchMethod.NONE,
            ifc_type=ifc
        )

    @pytest.fixture
    def bc3_only_pair(self):
        """Create a BC3-only pair."""
        bc3 = BC3Element(
            code="orphan",
            unit="m2",
            description="Orphan item",
            price=50.0
        )

        return MatchedPair(
            status=MatchStatus.BC3_ONLY,
            method=MatchMethod.NONE,
            bc3_element=bc3
        )

    def test_detect_property_mismatch(self, comparator, matched_pair_with_differences):
        """Test detection of property mismatches."""
        match_result = MatchResult(
            matched=[matched_pair_with_differences],
            ifc_only=[],
            bc3_only=[],
            match_count=1
        )

        result = comparator.compare(match_result)

        # Should detect h mismatch (0.6 vs 0.8) and Material mismatch
        errors = comparator.get_error_conflicts(result)
        assert len(errors) >= 1

        # Check for h property mismatch
        h_conflict = next((c for c in errors if c.property_name == "h"), None)
        assert h_conflict is not None
        assert h_conflict.ifc_value == 0.8
        assert h_conflict.bc3_value == 0.6

    def test_no_conflicts_when_identical(self, comparator, matched_pair_identical):
        """Test that identical pairs produce no property conflicts."""
        match_result = MatchResult(
            matched=[matched_pair_identical],
            ifc_only=[],
            bc3_only=[],
            match_count=1
        )

        result = comparator.compare(match_result)

        # Should have no ERROR conflicts
        errors = comparator.get_error_conflicts(result)
        assert len(errors) == 0

    def test_detect_missing_in_bc3(self, comparator, ifc_only_pair):
        """Test detection of elements missing from BC3."""
        match_result = MatchResult(
            matched=[],
            ifc_only=[ifc_only_pair],
            bc3_only=[],
            match_count=0
        )

        result = comparator.compare(match_result)

        assert result.missing_in_bc3 == 1
        missing = result.get_conflicts_by_type(ConflictType.MISSING_IN_BC3)
        assert len(missing) == 1
        assert missing[0].severity == ConflictSeverity.WARNING

    def test_detect_missing_in_ifc(self, comparator, bc3_only_pair):
        """Test detection of elements missing from IFC."""
        match_result = MatchResult(
            matched=[],
            ifc_only=[],
            bc3_only=[bc3_only_pair],
            match_count=0
        )

        result = comparator.compare(match_result)

        assert result.missing_in_ifc == 1
        missing = result.get_conflicts_by_type(ConflictType.MISSING_IN_IFC)
        assert len(missing) == 1

    def test_numeric_tolerance(self, comparator):
        """Test that numeric tolerance is applied."""
        bc3 = BC3Element(
            code="test",
            unit="m",
            description="Test",
            price=0,
            properties={"h": 0.600}
        )

        ifc = IFCType(
            global_id="guid",
            tag="test",
            name="Test",
            ifc_class="IfcBeamType",
            properties={"h": 0.605}  # Within 0.01 tolerance
        )

        pair = MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc,
            bc3_element=bc3,
            match_key="test"
        )

        match_result = MatchResult(matched=[pair], ifc_only=[], bc3_only=[], match_count=1)
        result = comparator.compare(match_result)

        # Should NOT detect a mismatch due to tolerance
        errors = comparator.get_error_conflicts(result)
        h_errors = [e for e in errors if e.property_name == "h"]
        assert len(h_errors) == 0

    def test_case_insensitive_string_comparison(self, comparator):
        """Test case-insensitive string comparison."""
        bc3 = BC3Element(
            code="test",
            unit="m",
            description="Test",
            price=0,
            properties={"Material": "CONCRETE"}
        )

        ifc = IFCType(
            global_id="guid",
            tag="test",
            name="Test",
            ifc_class="IfcWallType",
            properties={"Material": "concrete"}  # Different case
        )

        pair = MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc,
            bc3_element=bc3,
            match_key="test"
        )

        match_result = MatchResult(matched=[pair], ifc_only=[], bc3_only=[], match_count=1)
        result = comparator.compare(match_result)

        # Should NOT detect a mismatch due to case-insensitive comparison
        material_errors = [e for e in result.conflicts
                         if e.property_name == "Material" and
                         e.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(material_errors) == 0

    def test_summary_statistics(self, comparator, matched_pair_with_differences,
                                matched_pair_identical, ifc_only_pair, bc3_only_pair):
        """Test summary statistics."""
        match_result = MatchResult(
            matched=[matched_pair_with_differences, matched_pair_identical],
            ifc_only=[ifc_only_pair],
            bc3_only=[bc3_only_pair],
            match_count=2
        )

        result = comparator.compare(match_result)
        summary = result.summary()

        assert summary["total_matched"] == 2
        assert summary["missing_in_bc3"] == 1
        assert summary["missing_in_ifc"] == 1
        assert summary["property_mismatches"] >= 1


class TestPhase2PropertyListSelection:
    """Tests for Phase 2 property list selection (Issue #10)."""

    @pytest.fixture
    def comparator(self):
        return Comparator()

    @pytest.fixture
    def pair_with_spatial_and_material(self):
        """Create a pair with both spatial and material property differences."""
        bc3 = BC3Element(
            code="TEST001",
            unit="m",
            description="Test element",
            price=100.0,
            properties={
                "h": 2.5,        # Spatial - should be compared in spatial mode
                "b": 0.3,        # Spatial - should be compared
                "Material": "Concrete"  # Material - should NOT be compared in spatial mode
            }
        )

        ifc = IFCType(
            global_id="guid-test",
            tag="TEST001",
            name="Test:Element",
            ifc_class="IfcColumnType",
            properties={
                "h": 2.7,        # Different from BC3 (should flag in spatial)
                "b": 0.3,        # Same
                "Material": "Steel"  # Different but should NOT flag in spatial mode
            }
        )

        return MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc,
            bc3_element=bc3,
            match_key="TEST001"
        )

    def test_spatial_property_list_selected_by_default(self, comparator):
        """Test that SPATIAL_PROPERTIES is the default property list."""
        assert comparator._property_list == Comparator.SPATIAL_PROPERTIES

    def test_phase_config_spatial_selects_spatial_properties(self, comparator, pair_with_spatial_and_material):
        """Test that property_list='spatial' only compares spatial properties."""
        from src.phases.config import PhaseConfig

        config = PhaseConfig(
            name="Test Phase",
            check_properties=True,
            property_list="spatial"  # Only compare h, w, d
        )

        match_result = MatchResult(
            matched=[pair_with_spatial_and_material],
            ifc_only=[],
            bc3_only=[],
            match_count=1
        )

        result = comparator.compare(match_result, config)

        # Should detect h mismatch (2.5 vs 2.7) - spatial property
        h_conflicts = [c for c in result.conflicts
                      if c.property_name == "h" and c.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(h_conflicts) == 1

        # Should NOT detect Material mismatch - material property not in spatial list
        material_conflicts = [c for c in result.conflicts
                            if c.property_name == "Material" and c.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(material_conflicts) == 0

    def test_phase_config_all_selects_all_properties(self, comparator, pair_with_spatial_and_material):
        """Test that property_list='all' compares all properties including material."""
        from src.phases.config import PhaseConfig

        config = PhaseConfig(
            name="Test Phase",
            check_properties=True,
            property_list="all"  # Compare all properties
        )

        match_result = MatchResult(
            matched=[pair_with_spatial_and_material],
            ifc_only=[],
            bc3_only=[],
            match_count=1
        )

        result = comparator.compare(match_result, config)

        # Should detect h mismatch
        h_conflicts = [c for c in result.conflicts
                      if c.property_name == "h" and c.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(h_conflicts) == 1

        # Should also detect Material mismatch with 'all' property list
        material_conflicts = [c for c in result.conflicts
                            if c.property_name == "Material" and c.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(material_conflicts) == 1

    def test_quick_check_skips_properties(self, comparator, pair_with_spatial_and_material):
        """Test that QUICK_CHECK (check_properties=False) skips property comparison."""
        from src.phases.config import PhaseConfig

        config = PhaseConfig(
            name="Quick Check",
            check_properties=False,  # Skip property comparison
            property_list="spatial"
        )

        match_result = MatchResult(
            matched=[pair_with_spatial_and_material],
            ifc_only=[],
            bc3_only=[],
            match_count=1
        )

        result = comparator.compare(match_result, config)

        # Should NOT detect any property mismatches in quick check mode
        property_conflicts = [c for c in result.conflicts
                            if c.conflict_type == ConflictType.PROPERTY_MISMATCH]
        assert len(property_conflicts) == 0


class TestComparatorWithRealFiles:
    """Tests using real IFC and BC3 files."""

    @pytest.fixture
    def real_ifc_path(self):
        path = Path(__file__).parent.parent / "data" / "input" / "GUIA MODELADO V2.ifc"
        if not path.exists():
            pytest.skip(f"Real IFC file not found: {path}")
        return path

    @pytest.fixture
    def real_bc3_path(self):
        path = Path(__file__).parent.parent / "data" / "input" / "GUIA MODELADO V2 2025-12-18 06-47-01.bc3"
        if not path.exists():
            pytest.skip(f"Real BC3 file not found: {path}")
        return path

    def test_compare_real_files(self, real_ifc_path, real_bc3_path):
        """Test comparison with real files."""
        from src.parsers.ifc_parser import IFCParser
        from src.parsers.bc3_parser import BC3Parser
        from src.matching.matcher import Matcher

        ifc_parser = IFCParser()
        bc3_parser = BC3Parser()
        matcher = Matcher()
        comparator = Comparator()

        ifc_result = ifc_parser.parse(real_ifc_path)
        bc3_result = bc3_parser.parse(real_bc3_path)
        match_result = matcher.match(ifc_result, bc3_result)
        comparison = comparator.compare(match_result)

        print(f"\nComparison Results:")
        print(f"  Total conflicts: {len(comparison.conflicts)}")
        print(f"  Errors: {len(comparator.get_error_conflicts(comparison))}")
        print(f"  Warnings: {len(comparator.get_warning_conflicts(comparison))}")
        print(f"  Missing in BC3: {comparison.missing_in_bc3}")
        print(f"  Missing in IFC: {comparison.missing_in_ifc}")
        print(f"  Property mismatches: {comparison.property_mismatches}")

        # Should have some results
        assert comparison.total_matched > 0 or comparison.missing_in_bc3 > 0 or comparison.missing_in_ifc > 0
