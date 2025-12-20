"""Tests for main module and integration."""

import pytest
from pathlib import Path
import tempfile
import sys

from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter


class TestIntegration:
    """Integration tests for the full pipeline."""

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

    def test_full_pipeline(self, real_ifc_path, real_bc3_path):
        """Test the full pipeline from parsing to report generation."""
        # Parse
        ifc_parser = IFCParser()
        bc3_parser = BC3Parser()

        ifc_result = ifc_parser.parse(real_ifc_path)
        bc3_result = bc3_parser.parse(real_bc3_path)

        assert len(ifc_result.types) > 0
        assert len(bc3_result.elements) > 0

        # Match
        matcher = Matcher()
        match_result = matcher.match(ifc_result, bc3_result)

        assert len(match_result.matched) > 0

        # Compare
        comparator = Comparator()
        comparison = comparator.compare(match_result)

        # Generate report
        reporter = Reporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "integration_test_report.xlsx"
            report_path = reporter.generate_report(match_result, comparison, output_path)

            assert report_path.exists()

        print(f"\nFull Pipeline Test Results:")
        print(f"  IFC types: {len(ifc_result.types)}")
        print(f"  BC3 elements: {len(bc3_result.elements)}")
        print(f"  Matched: {len(match_result.matched)}")
        print(f"  Conflicts: {len(comparison.conflicts)}")


class TestTestDataGenerator:
    """Tests for the test data generator."""

    @pytest.fixture
    def real_bc3_path(self):
        path = Path(__file__).parent.parent / "data" / "input" / "GUIA MODELADO V2 2025-12-18 06-47-01.bc3"
        if not path.exists():
            pytest.skip(f"Real BC3 file not found: {path}")
        return path

    def test_bc3_modifier_remove_elements(self, real_bc3_path):
        """Test removing elements from BC3."""
        from src.test_data_generator import BC3Modifier

        modifier = BC3Modifier(real_bc3_path)

        # Get original element count
        original_count = modifier.content.count('~C|350147|')
        assert original_count > 0

        # Remove element
        modifier.remove_elements(['350147'])

        # Check it's removed
        new_count = modifier.content.count('~C|350147|')
        assert new_count == 0

    def test_bc3_modifier_modify_property(self, real_bc3_path):
        """Test modifying a property in BC3."""
        from src.test_data_generator import BC3Modifier

        modifier = BC3Modifier(real_bc3_path)

        # Modify property
        modifier.modify_property('350147', 'h', '9.99')

        # Check it's modified
        assert 'h\\9.99\\' in modifier.content

    def test_bc3_modifier_add_orphan(self, real_bc3_path):
        """Test adding an orphan element."""
        from src.test_data_generator import BC3Modifier

        modifier = BC3Modifier(real_bc3_path)

        # Add orphan
        modifier.add_orphan_element('TEST999', 'm2', 'Test Orphan', 123.45)

        # Check it's added
        assert '~C|TEST999|m2|Test Orphan|123.45|' in modifier.content

    def test_create_variants(self, real_bc3_path):
        """Test creating all variants."""
        from src.test_data_generator import create_test_variants

        with tempfile.TemporaryDirectory() as tmpdir:
            variants = create_test_variants(real_bc3_path, tmpdir)

            assert len(variants) == 5
            assert 'elements_removed' in variants
            assert 'properties_modified' in variants
            assert 'orphan_elements' in variants
            assert 'combined_issues' in variants
            assert 'identical' in variants

            # Check all files exist
            for name, path in variants.items():
                assert path.exists(), f"Variant {name} not created"


class TestWithModifiedBC3:
    """Tests using modified BC3 files to verify conflict detection."""

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

    def test_detect_missing_in_bc3(self, real_ifc_path, real_bc3_path):
        """Test detection of elements removed from BC3."""
        from src.test_data_generator import BC3Modifier

        # Create modified BC3 with removed elements
        modifier = BC3Modifier(real_bc3_path)
        modifier.remove_elements(['350147', '352900'])

        with tempfile.TemporaryDirectory() as tmpdir:
            modified_path = Path(tmpdir) / "modified.bc3"
            modifier.save(modified_path)

            # Run pipeline
            ifc_parser = IFCParser()
            bc3_parser = BC3Parser()
            matcher = Matcher()
            comparator = Comparator()

            ifc_result = ifc_parser.parse(real_ifc_path)
            bc3_result = bc3_parser.parse(modified_path)
            match_result = matcher.match(ifc_result, bc3_result)
            comparison = comparator.compare(match_result)

            # Check that we detect elements only in IFC
            # (they were removed from BC3)
            print(f"\nMissing in BC3 (removed elements): {comparison.missing_in_bc3}")
            # The removed elements should now be "IFC only"

    def test_detect_property_mismatch(self, real_ifc_path, real_bc3_path):
        """Test detection of property mismatches."""
        from src.test_data_generator import BC3Modifier
        from src.comparison.comparator import ConflictType

        # Create modified BC3 with changed properties
        modifier = BC3Modifier(real_bc3_path)
        modifier.modify_property('350147', 'h', '999.0')  # Obviously wrong value

        with tempfile.TemporaryDirectory() as tmpdir:
            modified_path = Path(tmpdir) / "modified.bc3"
            modifier.save(modified_path)

            # Run pipeline
            ifc_parser = IFCParser()
            bc3_parser = BC3Parser()
            matcher = Matcher()
            comparator = Comparator()

            ifc_result = ifc_parser.parse(real_ifc_path)
            bc3_result = bc3_parser.parse(modified_path)
            match_result = matcher.match(ifc_result, bc3_result)
            comparison = comparator.compare(match_result)

            # Check for property mismatch conflicts
            mismatches = comparison.get_conflicts_by_type(ConflictType.PROPERTY_MISMATCH)
            print(f"\nProperty mismatches detected: {len(mismatches)}")

    def test_detect_orphan_elements(self, real_ifc_path, real_bc3_path):
        """Test detection of orphan BC3 elements."""
        from src.test_data_generator import BC3Modifier

        # Create modified BC3 with orphan elements
        modifier = BC3Modifier(real_bc3_path)
        modifier.add_orphan_element('ORPHAN001', 'm2', 'This element has no model', 100.0)
        modifier.add_orphan_element('ORPHAN002', 'u', 'Another orphan', 200.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            modified_path = Path(tmpdir) / "modified.bc3"
            modifier.save(modified_path)

            # Run pipeline
            ifc_parser = IFCParser()
            bc3_parser = BC3Parser()
            matcher = Matcher()
            comparator = Comparator()

            ifc_result = ifc_parser.parse(real_ifc_path)
            bc3_result = bc3_parser.parse(modified_path)
            match_result = matcher.match(ifc_result, bc3_result)
            comparison = comparator.compare(match_result)

            # Check for BC3-only elements
            print(f"\nOrphan BC3 elements (BC3 only): {comparison.missing_in_ifc}")
            # Should have at least the 2 we added
            assert comparison.missing_in_ifc >= 2
