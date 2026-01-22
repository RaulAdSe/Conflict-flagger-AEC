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


class TestParameterComparison:
    """
    Tests for the new parameter comparison functionality added in PR #22.

    Tests cover:
    - _is_excluded_param() method
    - _compare_parameters() method
    - _format_parameter_discrepancies() method
    - PARAM_MAPPING and EXCLUDED_PARAMS class constants
    """

    @pytest.fixture
    def comparator(self):
        """Create a fresh comparator instance for testing."""
        return Comparator(tolerance=0.05)

    # =========================================================================
    # Tests for PARAM_MAPPING constant
    # =========================================================================

    def test_param_mapping_contains_height_variants(self, comparator):
        """Test that PARAM_MAPPING contains various height parameter mappings."""
        assert 'h' in comparator.PARAM_MAPPING
        assert 'altura' in comparator.PARAM_MAPPING
        assert 'ALTURA JACENA' in comparator.PARAM_MAPPING

        # Check that height params map to correct IFC properties
        assert 'Height' in comparator.PARAM_MAPPING['h']
        assert 'Altura' in comparator.PARAM_MAPPING['altura']

    def test_param_mapping_contains_width_variants(self, comparator):
        """Test that PARAM_MAPPING contains various width parameter mappings."""
        assert 'b' in comparator.PARAM_MAPPING
        assert 'anchura' in comparator.PARAM_MAPPING

        # Check that width params map to correct IFC properties
        assert 'Width' in comparator.PARAM_MAPPING['b']
        assert 'Anchura' in comparator.PARAM_MAPPING['anchura']

    def test_param_mapping_contains_thickness_variants(self, comparator):
        """Test that PARAM_MAPPING contains thickness parameter mappings."""
        assert 'grosor' in comparator.PARAM_MAPPING
        assert 'espesor' in comparator.PARAM_MAPPING
        assert 'e' in comparator.PARAM_MAPPING
        assert 'ALMA' in comparator.PARAM_MAPPING

    def test_param_mapping_contains_dimension_params(self, comparator):
        """Test that PARAM_MAPPING contains A1-A4 dimension parameters."""
        for dim in ['A1', 'A2', 'A3', 'A4']:
            assert dim in comparator.PARAM_MAPPING

    # =========================================================================
    # Tests for EXCLUDED_PARAMS constant
    # =========================================================================

    def test_excluded_params_contains_metadata_params(self, comparator):
        """Test that EXCLUDED_PARAMS contains metadata parameters."""
        metadata_params = ['ifcguid', 'nombre de familia', 'nombre de tipo',
                          'nota clave', 'marca de tipo']
        for param in metadata_params:
            assert param in comparator.EXCLUDED_PARAMS

    def test_excluded_params_contains_thermal_params(self, comparator):
        """Test that EXCLUDED_PARAMS contains thermal parameters."""
        thermal_params = ['coeficiente de transferencia de calor',
                         'resistencia térmica', 'masa térmica']
        for param in thermal_params:
            assert param in comparator.EXCLUDED_PARAMS

    def test_excluded_params_contains_cost_params(self, comparator):
        """Test that EXCLUDED_PARAMS contains cost-related parameters."""
        cost_params = ['costo', 'coste', 'precio']
        for param in cost_params:
            assert param in comparator.EXCLUDED_PARAMS

    # =========================================================================
    # Tests for _is_excluded_param() method
    # =========================================================================

    def test_is_excluded_param_returns_true_for_exact_match(self, comparator):
        """Test that _is_excluded_param returns True for exact matches."""
        assert comparator._is_excluded_param('ifcguid') is True
        assert comparator._is_excluded_param('costo') is True
        assert comparator._is_excluded_param('nombre de familia') is True

    def test_is_excluded_param_is_case_insensitive(self, comparator):
        """Test that _is_excluded_param is case-insensitive."""
        assert comparator._is_excluded_param('IFCGUID') is True
        assert comparator._is_excluded_param('IFCGuid') is True
        assert comparator._is_excluded_param('Costo') is True
        assert comparator._is_excluded_param('NOMBRE DE FAMILIA') is True

    def test_is_excluded_param_handles_whitespace(self, comparator):
        """Test that _is_excluded_param handles leading/trailing whitespace."""
        assert comparator._is_excluded_param('  ifcguid  ') is True
        assert comparator._is_excluded_param(' costo ') is True

    def test_is_excluded_param_matches_keywords(self, comparator):
        """Test that _is_excluded_param matches partial keywords."""
        # Contains 'guid'
        assert comparator._is_excluded_param('some_guid_value') is True
        assert comparator._is_excluded_param('tipo_guid_ref') is True

        # Contains 'omniclass'
        assert comparator._is_excluded_param('OmniClass Number') is True

        # Contains 'montaje'
        assert comparator._is_excluded_param('codigo montaje') is True

        # Contains 'comentarios'
        assert comparator._is_excluded_param('comentarios del tipo') is True

        # Contains 'cost'
        assert comparator._is_excluded_param('cost_estimate') is True

    def test_is_excluded_param_returns_false_for_dimensional_params(self, comparator):
        """Test that _is_excluded_param returns False for dimensional parameters."""
        dimensional_params = ['h', 'b', 'altura', 'anchura', 'longitud',
                             'Height', 'Width', 'Length', 'grosor']
        for param in dimensional_params:
            assert comparator._is_excluded_param(param) is False, f"'{param}' should not be excluded"

    def test_is_excluded_param_returns_false_for_quantity_params(self, comparator):
        """Test that _is_excluded_param returns False for quantity parameters."""
        quantity_params = ['NetArea', 'GrossArea', 'NetVolume', 'GrossVolume',
                          'A1', 'A2', 'ALMA']
        for param in quantity_params:
            assert comparator._is_excluded_param(param) is False, f"'{param}' should not be excluded"

    # =========================================================================
    # Tests for _compare_parameters() method
    # =========================================================================

    def test_compare_parameters_with_matching_values(self, comparator):
        """Test _compare_parameters with matching BC3 and IFC values."""
        # Create mock objects with properties attribute
        class MockBC3:
            properties = {'h': 0.6, 'b': 0.4}

        class MockIFC:
            properties = {'Height': 0.6, 'Width': 0.4}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 2
        # All should match (within tolerance)
        for c in comparisons:
            assert c['match'] is True

    def test_compare_parameters_with_mismatched_values(self, comparator):
        """Test _compare_parameters with mismatched BC3 and IFC values."""
        class MockBC3:
            properties = {'h': 0.6, 'b': 0.4}

        class MockIFC:
            properties = {'Height': 0.8, 'Width': 0.4}  # Height differs by >5%
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 2
        # h should not match (0.6 vs 0.8 = 25% difference)
        h_comp = next(c for c in comparisons if c['name'] == 'h')
        assert h_comp['match'] is False
        assert h_comp['bc3'] == 0.6
        assert h_comp['ifc'] == 0.8

        # b should match
        b_comp = next(c for c in comparisons if c['name'] == 'b')
        assert b_comp['match'] is True

    def test_compare_parameters_with_missing_ifc_property(self, comparator):
        """Test _compare_parameters when IFC is missing a property."""
        class MockBC3:
            properties = {'h': 0.6, 'b': 0.4, 'ALMA': 0.02}

        class MockIFC:
            properties = {'Height': 0.6}  # Missing Width and WebThickness
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 3

        # h should have IFC value
        h_comp = next(c for c in comparisons if c['name'] == 'h')
        assert h_comp['ifc'] == 0.6

        # b should have None IFC value
        b_comp = next(c for c in comparisons if c['name'] == 'b')
        assert b_comp['ifc'] is None

        # ALMA should have None IFC value
        alma_comp = next(c for c in comparisons if c['name'] == 'ALMA')
        assert alma_comp['ifc'] is None

    def test_compare_parameters_skips_excluded_params(self, comparator):
        """Test that _compare_parameters skips excluded parameters."""
        class MockBC3:
            properties = {
                'h': 0.6,
                'ifcguid': 'abc123',  # Excluded
                'costo': 150.0,       # Excluded
                'precio': 200.0       # Excluded
            }

        class MockIFC:
            properties = {'Height': 0.6}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # Only 'h' should be compared, excluded params should be skipped
        assert len(comparisons) == 1
        assert comparisons[0]['name'] == 'h'

    def test_compare_parameters_skips_zero_values(self, comparator):
        """Test that _compare_parameters skips zero BC3 values."""
        class MockBC3:
            properties = {'h': 0.6, 'b': 0, 'grosor': 0.0}

        class MockIFC:
            properties = {'Height': 0.6, 'Width': 0.4, 'Thickness': 0.1}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # Only 'h' should be compared (non-zero)
        assert len(comparisons) == 1
        assert comparisons[0]['name'] == 'h'

    def test_compare_parameters_skips_non_numeric_values(self, comparator):
        """Test that _compare_parameters skips non-numeric (string) BC3 values.

        Note: In Python, bool is a subclass of int, so True/False pass the
        isinstance(value, (int, float)) check. This test verifies strings are skipped.
        """
        class MockBC3:
            properties = {
                'h': 0.6,
                'Material': 'Concrete',  # String - should be skipped
                'Description': 'Test beam'  # String - should be skipped
            }

        class MockIFC:
            properties = {'Height': 0.6}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # Only 'h' should be compared (strings are skipped)
        assert len(comparisons) == 1
        assert comparisons[0]['name'] == 'h'

    def test_compare_parameters_uses_quantities_dict(self, comparator):
        """Test that _compare_parameters checks both properties and quantities dicts."""
        class MockBC3:
            properties = {'longitud': 5.5, 'h': 0.6}

        class MockIFC:
            properties = {'Height': 0.6}
            quantities = {'Length': 5.5}  # Length is in quantities, not properties

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 2

        # longitud should map to Length in quantities
        long_comp = next(c for c in comparisons if c['name'] == 'longitud')
        assert long_comp['ifc'] == 5.5
        assert long_comp['match'] is True

    def test_compare_parameters_case_insensitive_ifc_lookup(self, comparator):
        """Test that _compare_parameters does case-insensitive IFC property lookup."""
        class MockBC3:
            properties = {'h': 0.6}

        class MockIFC:
            properties = {'height': 0.6}  # lowercase, but should still match
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 1
        assert comparisons[0]['ifc'] == 0.6
        assert comparisons[0]['match'] is True

    def test_compare_parameters_empty_bc3_properties(self, comparator):
        """Test _compare_parameters with empty BC3 properties."""
        class MockBC3:
            properties = {}

        class MockIFC:
            properties = {'Height': 0.6}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 0

    def test_compare_parameters_none_properties(self, comparator):
        """Test _compare_parameters when properties attribute is None."""
        class MockBC3:
            properties = None

        class MockIFC:
            properties = None
            quantities = None

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        assert len(comparisons) == 0

    def test_compare_parameters_all_excluded(self, comparator):
        """Test _compare_parameters when all BC3 params are excluded."""
        class MockBC3:
            properties = {
                'ifcguid': 'guid123',
                'costo': 100.0,
                'precio': 150.0,
                'nombre de familia': 'Test'
            }

        class MockIFC:
            properties = {}
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # All params are excluded, so no comparisons
        assert len(comparisons) == 0

    def test_compare_parameters_tolerance_boundary(self, comparator):
        """Test _compare_parameters at the 5% tolerance boundary."""
        class MockBC3:
            properties = {'h': 1.0}

        class MockIFC:
            properties = {'Height': 1.05}  # Exactly 5% difference
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # 5% is the boundary - should still match
        assert comparisons[0]['match'] is True

        # Now test just over 5%
        class MockIFC2:
            properties = {'Height': 1.06}  # 6% difference
            quantities = {}

        ifc_type2 = MockIFC2()
        comparisons2 = comparator._compare_parameters(ifc_type2, bc3_elem)

        # Over 5% should not match
        assert comparisons2[0]['match'] is False

    # =========================================================================
    # Tests for _format_parameter_discrepancies() method
    # =========================================================================

    def test_format_parameter_discrepancies_empty_list(self, comparator):
        """Test _format_parameter_discrepancies with empty comparisons list."""
        result = comparator._format_parameter_discrepancies([])
        assert result == "Cantidad"

    def test_format_parameter_discrepancies_single_param_with_ifc(self, comparator):
        """Test formatting a single parameter comparison with IFC value."""
        comparisons = [{'name': 'h', 'bc3': 0.6, 'ifc': 0.65, 'match': False}]

        result = comparator._format_parameter_discrepancies(comparisons)

        assert 'h' in result
        assert 'bc3: 0,60' in result
        assert 'ifc: 0,65' in result

    def test_format_parameter_discrepancies_single_param_without_ifc(self, comparator):
        """Test formatting a single parameter comparison without IFC value."""
        comparisons = [{'name': 'h', 'bc3': 0.6, 'ifc': None, 'match': True}]

        result = comparator._format_parameter_discrepancies(comparisons)

        assert 'h' in result
        assert 'bc3: 0,60' in result
        assert 'ifc' not in result  # No IFC value shown

    def test_format_parameter_discrepancies_multiple_params(self, comparator):
        """Test formatting multiple parameter comparisons."""
        comparisons = [
            {'name': 'h', 'bc3': 0.6, 'ifc': 0.65, 'match': False},
            {'name': 'b', 'bc3': 0.4, 'ifc': 0.4, 'match': True},
            {'name': 'ALMA', 'bc3': 0.02, 'ifc': None, 'match': True}
        ]

        result = comparator._format_parameter_discrepancies(comparisons)

        # All params should be present, separated by semicolons
        assert 'h' in result
        assert 'b' in result
        assert 'ALMA' in result
        assert ';' in result

    def test_format_parameter_discrepancies_uses_spanish_decimal(self, comparator):
        """Test that formatting uses comma as decimal separator (Spanish format)."""
        comparisons = [{'name': 'h', 'bc3': 1.234, 'ifc': 5.678, 'match': False}]

        result = comparator._format_parameter_discrepancies(comparisons)

        # Should use comma as decimal separator
        assert '1,23' in result
        assert '5,68' in result
        # Should not contain dot as decimal separator
        assert '1.23' not in result
        assert '5.68' not in result

    def test_format_parameter_discrepancies_preserves_param_names(self, comparator):
        """Test that original parameter names are preserved in output."""
        comparisons = [
            {'name': 'ALTURA JACENA', 'bc3': 0.6, 'ifc': 0.65, 'match': False},
            {'name': 'ANCHURA JACENA', 'bc3': 0.4, 'ifc': None, 'match': True}
        ]

        result = comparator._format_parameter_discrepancies(comparisons)

        assert 'ALTURA JACENA' in result
        assert 'ANCHURA JACENA' in result

    def test_format_parameter_discrepancies_format_structure(self, comparator):
        """Test the exact format structure of the output."""
        comparisons = [{'name': 'h', 'bc3': 0.6, 'ifc': 0.65, 'match': False}]

        result = comparator._format_parameter_discrepancies(comparisons)

        # Expected format: "h (bc3: 0,60, ifc: 0,65)"
        assert result == "h (bc3: 0,60, ifc: 0,65)"

    def test_format_parameter_discrepancies_format_without_ifc(self, comparator):
        """Test the exact format structure when IFC value is missing."""
        comparisons = [{'name': 'h', 'bc3': 0.6, 'ifc': None, 'match': True}]

        result = comparator._format_parameter_discrepancies(comparisons)

        # Expected format: "h (bc3: 0,60)"
        assert result == "h (bc3: 0,60)"

    def test_format_parameter_discrepancies_multiple_format(self, comparator):
        """Test the exact format with multiple parameters."""
        comparisons = [
            {'name': 'h', 'bc3': 0.6, 'ifc': 0.65, 'match': False},
            {'name': 'b', 'bc3': 0.4, 'ifc': None, 'match': True}
        ]

        result = comparator._format_parameter_discrepancies(comparisons)

        # Expected format: "h (bc3: 0,60, ifc: 0,65); b (bc3: 0,40)"
        assert result == "h (bc3: 0,60, ifc: 0,65); b (bc3: 0,40)"

    # =========================================================================
    # Integration tests combining the methods
    # =========================================================================

    def test_integration_compare_and_format(self, comparator):
        """Test full flow from _compare_parameters to _format_parameter_discrepancies."""
        class MockBC3:
            properties = {'h': 0.6, 'b': 0.4, 'ALMA': 0.02}

        class MockIFC:
            properties = {'Height': 0.65}  # Only Height available
            quantities = {}

        bc3_elem = MockBC3()
        ifc_type = MockIFC()

        # First compare
        comparisons = comparator._compare_parameters(ifc_type, bc3_elem)

        # Then format
        result = comparator._format_parameter_discrepancies(comparisons)

        # Should contain all three parameters
        assert 'h' in result
        assert 'b' in result
        assert 'ALMA' in result

        # h should have both values
        assert 'ifc: 0,65' in result

        # b and ALMA should only have bc3 values
        assert result.count('ifc:') == 1  # Only one IFC value (for h)
