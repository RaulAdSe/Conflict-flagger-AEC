"""Tests for Matcher."""

import pytest
from pathlib import Path

from src.parsers.bc3_parser import BC3Parser, BC3Element, BC3ParseResult
from src.parsers.ifc_parser import IFCParser, IFCElement, IFCType, IFCParseResult
from src.matching.matcher import (
    Matcher, MatchMethod, MatchStatus, MatchedPair, MatchResult,
    normalize_description, calculate_similarity
)
from src.matching.filters import is_ignored_element, filter_elements, IGNORE_TERMS


# =============================================================================
# TESTS FOR SIMILARITY FUNCTIONS
# =============================================================================

class TestSimilarityFunctions:
    """Tests for text similarity functions."""

    def test_normalize_description_basic(self):
        """Test basic normalization."""
        assert normalize_description("Hello World") == "hello world"
        assert normalize_description("UPPERCASE") == "uppercase"

    def test_normalize_description_special_chars(self):
        """Test removal of special characters."""
        result = normalize_description("Pilar - 600 x 600 mm")
        assert result == "pilar 600 x 600 mm"

    def test_normalize_description_accents(self):
        """Test preservation of accented characters."""
        result = normalize_description("Jácena metálica")
        assert "jácena" in result
        assert "metálica" in result

    def test_normalize_description_empty(self):
        """Test empty/None handling."""
        assert normalize_description("") == ""
        assert normalize_description(None) == ""

    def test_calculate_similarity_identical(self):
        """Test similarity of identical descriptions."""
        score = calculate_similarity(
            "Pilar rectangular hormigón 600 x 600",
            "Pilar rectangular hormigón 600 x 600"
        )
        assert score == 1.0

    def test_calculate_similarity_similar(self):
        """Test similarity of similar descriptions."""
        score = calculate_similarity(
            "Pilar rectangular hormigón 600 x 600 mm",
            "Pilar rectangular hormigón - 600 x 600"
        )
        # Should be high (>0.7) due to shared words
        assert score > 0.7

    def test_calculate_similarity_different(self):
        """Test similarity of different descriptions."""
        score = calculate_similarity(
            "Pilar hormigón",
            "Ventana aluminio"
        )
        # Should be low (<0.3) due to no shared words
        assert score < 0.3

    def test_calculate_similarity_stopwords(self):
        """Test that stopwords are ignored."""
        # "de la el" are stopwords
        score = calculate_similarity(
            "Pilar de hormigón",
            "Pilar hormigón"
        )
        # Should be high because "de" is ignored
        assert score > 0.8

    def test_calculate_similarity_empty(self):
        """Test similarity with empty strings."""
        assert calculate_similarity("", "test") == 0.0
        assert calculate_similarity("test", "") == 0.0
        assert calculate_similarity("", "") == 0.0


# =============================================================================
# TESTS FOR FILTERS
# =============================================================================

class TestFilters:
    """Tests for element filters."""

    def test_is_ignored_element_views(self):
        """Test ignoring view-related elements."""
        assert is_ignored_element(None, "Project Info") is True
        assert is_ignored_element(None, "Vista de plano") is True
        assert is_ignored_element(None, "Sheet 1") is True

    def test_is_ignored_element_rooms(self):
        """Test ignoring room-related elements."""
        assert is_ignored_element(None, "Habitaciones") is True
        assert is_ignored_element(None, "Zona de climatización") is True
        assert is_ignored_element(None, "Áreas") is True

    def test_is_ignored_element_openings(self):
        """Test ignoring openings."""
        assert is_ignored_element(None, "Opening") is True
        assert is_ignored_element(None, "Hueco de ventana") is True
        assert is_ignored_element(None, "Void cut") is True

    def test_is_ignored_element_building_elements(self):
        """Test that building elements are NOT ignored."""
        assert is_ignored_element(None, "Pilar rectangular hormigón") is False
        assert is_ignored_element(None, "Muro de ladrillo") is False
        assert is_ignored_element(None, "Ventana de aluminio") is False
        assert is_ignored_element("350147", "Jácena metálica") is False

    def test_is_ignored_element_code_check(self):
        """Test that code is also checked."""
        # Even with normal description, if code contains ignore term
        assert is_ignored_element("sheet_01", "Normal description") is True

    def test_is_ignored_element_case_insensitive(self):
        """Test case insensitivity."""
        assert is_ignored_element(None, "PROJECT INFO") is True
        assert is_ignored_element(None, "SHEET") is True

    def test_filter_elements(self):
        """Test filtering a dictionary of elements."""
        # Create mock elements
        class MockElement:
            def __init__(self, code, description):
                self.code = code
                self.description = description

        elements = {
            "1": MockElement("1", "Pilar hormigón"),
            "2": MockElement("2", "Project Info"),
            "3": MockElement("3", "Muro ladrillo"),
            "4": MockElement("4", "Sheet view"),
        }

        filtered = filter_elements(elements)

        # Should only have building elements
        assert "1" in filtered
        assert "2" not in filtered
        assert "3" in filtered
        assert "4" not in filtered


class TestMatchedPair:
    """Tests for MatchedPair dataclass."""

    def test_create_matched_pair(self):
        """Test creating a matched pair."""
        bc3_elem = BC3Element(
            code="350147",
            unit="m3",
            description="Pilar rectangular hormigón - 600 x 600 mm",
            price=150.0
        )
        ifc_type = IFCType(
            global_id="2yt6D8WIv1pOA$7fKuaiRG",
            tag="350147",
            name="Pilar rectangular hormigón:600 x 600 mm",
            ifc_class="IfcColumnType"
        )

        pair = MatchedPair(
            status=MatchStatus.MATCHED,
            method=MatchMethod.TAG,
            ifc_type=ifc_type,
            bc3_element=bc3_elem,
            match_key="350147"
        )

        assert pair.status == MatchStatus.MATCHED
        assert pair.method == MatchMethod.TAG
        assert pair.code == "350147"
        assert pair.confidence == 1.0

    def test_ifc_only_pair(self):
        """Test creating an IFC-only pair."""
        ifc_type = IFCType(
            global_id="abc123",
            tag="999",
            name="Test Type",
            ifc_class="IfcWallType"
        )

        pair = MatchedPair(
            status=MatchStatus.IFC_ONLY,
            method=MatchMethod.NONE,
            ifc_type=ifc_type
        )

        assert pair.status == MatchStatus.IFC_ONLY
        assert pair.bc3_element is None
        assert pair.code == "999"

    def test_bc3_only_pair(self):
        """Test creating a BC3-only pair."""
        bc3_elem = BC3Element(
            code="orphan123",
            unit="m2",
            description="Orphan budget item",
            price=100.0
        )

        pair = MatchedPair(
            status=MatchStatus.BC3_ONLY,
            method=MatchMethod.NONE,
            bc3_element=bc3_elem
        )

        assert pair.status == MatchStatus.BC3_ONLY
        assert pair.ifc_type is None
        assert pair.code == "orphan123"


class TestMatchResult:
    """Tests for MatchResult dataclass."""

    def test_match_rate(self):
        """Test match rate calculation."""
        result = MatchResult(
            matched=[],
            ifc_only=[],
            bc3_only=[],
            total_ifc_types=10,
            total_bc3_elements=10,
            match_count=5
        )

        # 5 matches cover 10 items out of 20 total = 50%
        assert result.match_rate == 50.0

    def test_summary(self):
        """Test summary generation."""
        result = MatchResult(
            matched=[1, 2, 3],  # Mock pairs
            ifc_only=[4],
            bc3_only=[5, 6],
            total_ifc_types=4,
            total_bc3_elements=5,
            match_count=3
        )

        summary = result.summary()
        assert summary["matched"] == 3
        assert summary["ifc_only"] == 1
        assert summary["bc3_only"] == 2


class TestMatcher:
    """Tests for Matcher class."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher instance."""
        return Matcher()

    @pytest.fixture
    def mock_ifc_result(self):
        """Create mock IFC parse result."""
        types = {
            "guid1": IFCType(
                global_id="guid1",
                tag="350147",
                name="Pilar:600x600",
                ifc_class="IfcColumnType",
                family_name="Pilar",
                type_name="600x600"
            ),
            "guid2": IFCType(
                global_id="guid2",
                tag="352900",
                name="Jácena:I-220",
                ifc_class="IfcBeamType",
                family_name="Jácena",
                type_name="I-220"
            ),
            "guid3": IFCType(
                global_id="guid3",
                tag="999999",
                name="Unmatched:Type",
                ifc_class="IfcSlabType"
            )
        }

        return IFCParseResult(
            elements={},
            types=types,
            elements_by_tag={},
            types_by_tag={"350147": types["guid1"], "352900": types["guid2"], "999999": types["guid3"]},
            schema="IFC2X3",
            project_name="Test Project"
        )

    @pytest.fixture
    def mock_bc3_result(self):
        """Create mock BC3 parse result."""
        elements = {
            "350147": BC3Element(
                code="350147",
                unit="m3",
                description="Pilar 600x600",
                price=150.0,
                type_ifc_guid="guid1",
                family_name="Pilar",
                type_name="600x600"
            ),
            "352900": BC3Element(
                code="352900",
                unit="m",
                description="Jácena I-220",
                price=200.0,
                type_ifc_guid="guid2"
            ),
            "orphan": BC3Element(
                code="orphan",
                unit="m2",
                description="Orphan BC3 item",
                price=50.0
            )
        }

        return BC3ParseResult(
            elements=elements,
            hierarchy={},
            version="FIEBDC-3/2020"
        )

    def test_match_by_tag(self, matcher, mock_ifc_result, mock_bc3_result):
        """Test matching by tag."""
        result = matcher.match(mock_ifc_result, mock_bc3_result)

        # Should have 2 matches (350147 and 352900)
        tag_matches = matcher.get_matched_by_method(result, MatchMethod.TAG)
        assert len(tag_matches) == 2

        codes = {m.code for m in tag_matches}
        assert "350147" in codes
        assert "352900" in codes

    def test_ifc_only_detection(self, matcher, mock_ifc_result, mock_bc3_result):
        """Test detection of IFC-only items."""
        result = matcher.match(mock_ifc_result, mock_bc3_result)

        # guid3 (tag 999999) should be IFC-only
        assert len(result.ifc_only) == 1
        assert result.ifc_only[0].ifc_type.tag == "999999"

    def test_bc3_only_detection(self, matcher, mock_ifc_result, mock_bc3_result):
        """Test detection of BC3-only items."""
        result = matcher.match(mock_ifc_result, mock_bc3_result)

        # "orphan" should be BC3-only
        assert len(result.bc3_only) == 1
        assert result.bc3_only[0].bc3_element.code == "orphan"

    def test_match_by_guid(self, matcher):
        """Test matching by GUID when tag doesn't match."""
        # IFC type without matching tag but with GUID
        ifc_types = {
            "special_guid": IFCType(
                global_id="special_guid",
                tag="different_tag",
                name="Special Type",
                ifc_class="IfcWallType"
            )
        }
        ifc_result = IFCParseResult(
            elements={},
            types=ifc_types,
            elements_by_tag={},
            types_by_tag={"different_tag": ifc_types["special_guid"]},
            schema="IFC2X3",
            project_name="Test"
        )

        # BC3 element with matching GUID but different code
        bc3_elements = {
            "bc3_code": BC3Element(
                code="bc3_code",
                unit="m2",
                description="BC3 Element",
                price=100.0,
                type_ifc_guid="special_guid"
            )
        }
        bc3_result = BC3ParseResult(
            elements=bc3_elements,
            hierarchy={},
            version="test"
        )

        result = matcher.match(ifc_result, bc3_result)

        guid_matches = matcher.get_matched_by_method(result, MatchMethod.GUID)
        assert len(guid_matches) == 1
        assert guid_matches[0].match_key == "special_guid"

    def test_high_confidence_matches(self, matcher, mock_ifc_result, mock_bc3_result):
        """Test filtering high confidence matches."""
        result = matcher.match(mock_ifc_result, mock_bc3_result)

        high_conf = matcher.get_high_confidence_matches(result, threshold=0.9)
        # Tag and GUID matches have confidence 1.0
        assert len(high_conf) == 2

    def test_summary_stats(self, matcher, mock_ifc_result, mock_bc3_result):
        """Test summary statistics."""
        result = matcher.match(mock_ifc_result, mock_bc3_result)

        summary = result.summary()
        assert summary["matched"] == 2
        assert summary["ifc_only"] == 1
        assert summary["bc3_only"] == 1

    def test_match_by_description(self):
        """Test matching by description similarity when codes differ."""
        matcher = Matcher(match_by_description=True, similarity_threshold=0.5)

        # IFC type with one code
        ifc_types = {
            "guid1": IFCType(
                global_id="guid1",
                tag="171671",  # Original code
                name="Descansillo monolítico - 220mm Thickness",
                ifc_class="IfcSlabType"
            )
        }
        ifc_result = IFCParseResult(
            elements={},
            types=ifc_types,
            elements_by_tag={},
            types_by_tag={"171671": ifc_types["guid1"]},
            schema="IFC2X3",
            project_name="Test"
        )

        # BC3 element with DIFFERENT code but SIMILAR description
        bc3_elements = {
            "171999": BC3Element(  # Different code!
                code="171999",
                unit="u",
                description="Descansillo monolítico - 220mm Thickness",
                price=100.0
            )
        }
        bc3_result = BC3ParseResult(
            elements=bc3_elements,
            hierarchy={},
            version="test"
        )

        result = matcher.match(ifc_result, bc3_result)

        # Should match by description since codes don't match
        desc_matches = matcher.get_matched_by_method(result, MatchMethod.DESCRIPTION)
        assert len(desc_matches) == 1
        assert desc_matches[0].bc3_element.code == "171999"
        assert desc_matches[0].ifc_type.tag == "171671"
        assert desc_matches[0].confidence <= 0.8  # Description matches capped at 0.8

    def test_match_by_description_disabled(self):
        """Test that description matching can be disabled."""
        matcher = Matcher(match_by_description=False)

        ifc_types = {
            "guid1": IFCType(
                global_id="guid1",
                tag="code1",
                name="Similar Description Here",
                ifc_class="IfcSlabType"
            )
        }
        ifc_result = IFCParseResult(
            elements={},
            types=ifc_types,
            elements_by_tag={},
            types_by_tag={"code1": ifc_types["guid1"]},
            schema="IFC2X3",
            project_name="Test"
        )

        bc3_elements = {
            "code2": BC3Element(
                code="code2",
                unit="u",
                description="Similar Description Here",
                price=100.0
            )
        }
        bc3_result = BC3ParseResult(
            elements=bc3_elements,
            hierarchy={},
            version="test"
        )

        result = matcher.match(ifc_result, bc3_result)

        # Should NOT match when description matching is disabled
        desc_matches = matcher.get_matched_by_method(result, MatchMethod.DESCRIPTION)
        assert len(desc_matches) == 0
        assert len(result.ifc_only) == 1
        assert len(result.bc3_only) == 1


class TestMatcherWithRealFiles:
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

    def test_match_real_files(self, real_ifc_path, real_bc3_path):
        """Test matching real IFC and BC3 files."""
        ifc_parser = IFCParser()
        bc3_parser = BC3Parser()
        matcher = Matcher()

        ifc_result = ifc_parser.parse(real_ifc_path)
        bc3_result = bc3_parser.parse(real_bc3_path)

        result = matcher.match(ifc_result, bc3_result)

        print(f"\nMatch Results:")
        print(f"  Total IFC types: {result.total_ifc_types}")
        print(f"  Total BC3 elements: {result.total_bc3_elements}")
        print(f"  Matched: {len(result.matched)}")
        print(f"  IFC only: {len(result.ifc_only)}")
        print(f"  BC3 only: {len(result.bc3_only)}")
        print(f"  Match rate: {result.match_rate:.1f}%")

        # Should have some matches
        assert len(result.matched) > 0

        # Check match methods
        tag_matches = matcher.get_matched_by_method(result, MatchMethod.TAG)
        guid_matches = matcher.get_matched_by_method(result, MatchMethod.GUID)
        print(f"  By tag: {len(tag_matches)}")
        print(f"  By GUID: {len(guid_matches)}")

    def test_specific_matches(self, real_ifc_path, real_bc3_path):
        """Test specific known matches."""
        ifc_parser = IFCParser()
        bc3_parser = BC3Parser()
        matcher = Matcher()

        ifc_result = ifc_parser.parse(real_ifc_path)
        bc3_result = bc3_parser.parse(real_bc3_path)

        result = matcher.match(ifc_result, bc3_result)

        # Check for specific element we know should match
        matched_codes = {m.code for m in result.matched}

        # These should be in the matches (from our earlier analysis)
        expected_matches = ["350147", "352900", "350145"]
        for code in expected_matches:
            if code in bc3_result.elements and code in ifc_result.types_by_tag:
                assert code in matched_codes, f"Expected {code} to be matched"
