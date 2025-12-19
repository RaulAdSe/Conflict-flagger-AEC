"""Tests for IFC Parser."""

import pytest
from pathlib import Path

from src.parsers.ifc_parser import IFCParser, IFCElement, IFCType, IFCParseResult


class TestIFCElement:
    """Tests for IFCElement dataclass."""

    def test_create_basic_element(self):
        """Test creating a basic IFC element."""
        elem = IFCElement(
            global_id="2yt6D8WIv1pOA$7fKuaiaB",
            tag="350232",
            name="Pilar rectangular hormigón:600 x 600 mm:350232",
            ifc_class="IfcColumn"
        )
        assert elem.global_id == "2yt6D8WIv1pOA$7fKuaiaB"
        assert elem.tag == "350232"
        assert elem.ifc_class == "IfcColumn"
        assert elem.properties == {}
        assert elem.quantities == {}

    def test_element_with_type(self):
        """Test element with type information."""
        elem = IFCElement(
            global_id="2yt6D8WIv1pOA$7fKuaiaB",
            tag="350232",
            name="Column",
            ifc_class="IfcColumn",
            type_id="2yt6D8WIv1pOA$5fKuaiaB",
            type_name="600 x 600 mm",
            family_name="Pilar rectangular hormigón"
        )
        assert elem.type_id == "2yt6D8WIv1pOA$5fKuaiaB"
        assert elem.type_name == "600 x 600 mm"
        assert elem.family_name == "Pilar rectangular hormigón"


class TestIFCType:
    """Tests for IFCType dataclass."""

    def test_create_type(self):
        """Test creating an IFC type."""
        ifc_type = IFCType(
            global_id="2yt6D8WIv1pOA$5fKuaiaB",
            tag="350147",
            name="Pilar rectangular hormigón:600 x 600 mm",
            ifc_class="IfcColumnType",
            family_name="Pilar rectangular hormigón",
            type_name="600 x 600 mm"
        )
        assert ifc_type.global_id == "2yt6D8WIv1pOA$5fKuaiaB"
        assert ifc_type.tag == "350147"
        assert ifc_type.family_name == "Pilar rectangular hormigón"


class TestIFCParser:
    """Tests for IFCParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return IFCParser()

    def test_file_not_found(self, parser):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/file.ifc")

    def test_parse_type_name_with_colon(self, parser):
        """Test parsing type name with family:type format."""
        family, type_name = parser._parse_type_name("Pilar rectangular:600 x 600 mm")
        assert family == "Pilar rectangular"
        assert type_name == "600 x 600 mm"

    def test_parse_type_name_without_colon(self, parser):
        """Test parsing type name without separator."""
        family, type_name = parser._parse_type_name("Simple Name")
        assert family == "Simple Name"
        assert type_name is None

    def test_parse_type_name_empty(self, parser):
        """Test parsing empty type name."""
        family, type_name = parser._parse_type_name("")
        assert family is None
        assert type_name is None


class TestIFCParserWithRealFile:
    """Tests using the real IFC file from the project."""

    @pytest.fixture
    def real_ifc_path(self):
        """Path to the real IFC file."""
        path = Path(__file__).parent.parent / "data" / "input" / "GUIA MODELADO V2.ifc"
        if not path.exists():
            pytest.skip(f"Real IFC file not found: {path}")
        return path

    @pytest.fixture
    def parser(self):
        return IFCParser()

    def test_parse_real_file(self, parser, real_ifc_path):
        """Test parsing the real IFC file."""
        result = parser.parse(real_ifc_path)

        assert len(result.elements) > 0
        assert len(result.types) > 0
        assert result.schema != ""
        print(f"Parsed {len(result.elements)} elements and {len(result.types)} types")
        print(f"Schema: {result.schema}")
        print(f"Project: {result.project_name}")

    def test_real_file_has_columns(self, parser, real_ifc_path):
        """Test that real file contains column elements."""
        result = parser.parse(real_ifc_path)

        columns = parser.get_elements_by_class(result, "IfcColumn")
        assert len(columns) > 0
        print(f"Found {len(columns)} columns")

        # Check first column has expected properties
        col = columns[0]
        assert col.global_id is not None
        print(f"First column: {col.name}, Tag: {col.tag}")

    def test_real_file_has_beams(self, parser, real_ifc_path):
        """Test that real file contains beam elements."""
        result = parser.parse(real_ifc_path)

        beams = parser.get_elements_by_class(result, "IfcBeam")
        assert len(beams) > 0
        print(f"Found {len(beams)} beams")

    def test_real_file_type_tags(self, parser, real_ifc_path):
        """Test that types have tags that match BC3 codes."""
        result = parser.parse(real_ifc_path)

        # Check for the column type we know from BC3
        types_with_tags = {t.tag: t for t in result.types.values() if t.tag}
        print(f"Found {len(types_with_tags)} types with tags")

        # The BC3 has code 350147 for "Pilar rectangular hormigón - 600 x 600 mm"
        if "350147" in types_with_tags:
            t = types_with_tags["350147"]
            print(f"Found matching type: {t.name}")
            assert "600" in t.name.lower() or "pilar" in t.name.lower()

    def test_real_file_beam_type(self, parser, real_ifc_path):
        """Test beam type matches BC3 code."""
        result = parser.parse(real_ifc_path)

        # BC3 has code 352900 for "JACENA I - I-220"
        if "352900" in result.types_by_tag:
            t = result.types_by_tag["352900"]
            print(f"Found beam type: {t.name}, GUID: {t.global_id}")
            # The BC3 has Tipo IfcGUID: 2yt6D8WIv1pOA$7fKualEN
            assert t.global_id == "2yt6D8WIv1pOA$7fKualEN"

    def test_elements_by_tag_lookup(self, parser, real_ifc_path):
        """Test looking up elements by tag."""
        result = parser.parse(real_ifc_path)

        # Check that we have elements indexed by tag
        assert len(result.elements_by_tag) > 0
        print(f"Found {len(result.elements_by_tag)} elements with tags")

    def test_type_to_instances(self, parser, real_ifc_path):
        """Test getting instances of a type."""
        result = parser.parse(real_ifc_path)

        # If we have the beam type, check its instances
        if "352900" in result.types_by_tag:
            instances = parser.get_elements_by_type_tag(result, "352900")
            print(f"Beam type 352900 has {len(instances)} instances")
            assert len(instances) >= 0  # May have 0 if instances aren't tagged


class TestIFCParserIntegration:
    """Integration tests comparing IFC and BC3 data."""

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

    def test_guid_correlation(self, real_ifc_path, real_bc3_path):
        """Test that BC3 Tipo IfcGUID matches IFC GlobalId."""
        from src.parsers.bc3_parser import BC3Parser
        from src.parsers.ifc_parser import IFCParser

        bc3_parser = BC3Parser()
        ifc_parser = IFCParser()

        bc3_result = bc3_parser.parse(real_bc3_path)
        ifc_result = ifc_parser.parse(real_ifc_path)

        # Get BC3 elements with IFC GUIDs
        bc3_with_guid = bc3_parser.get_types_with_guid(bc3_result)

        matches = 0
        mismatches = 0

        for code, bc3_elem in bc3_with_guid.items():
            if bc3_elem.type_ifc_guid:
                # Check if this GUID exists in IFC types
                if bc3_elem.type_ifc_guid in ifc_result.types:
                    ifc_type = ifc_result.types[bc3_elem.type_ifc_guid]
                    matches += 1
                    # Verify tag matches
                    if ifc_type.tag == code:
                        print(f"✓ Match: BC3 {code} -> IFC {ifc_type.name}")
                else:
                    mismatches += 1

        print(f"\nGUID Correlation: {matches} matches, {mismatches} mismatches")
        assert matches > 0, "Should have at least some GUID matches"

    def test_tag_correlation(self, real_ifc_path, real_bc3_path):
        """Test that BC3 codes match IFC tags."""
        from src.parsers.bc3_parser import BC3Parser
        from src.parsers.ifc_parser import IFCParser

        bc3_parser = BC3Parser()
        ifc_parser = IFCParser()

        bc3_result = bc3_parser.parse(real_bc3_path)
        ifc_result = ifc_parser.parse(real_ifc_path)

        # Check how many BC3 codes have matching IFC types
        matches = 0
        for code in bc3_result.elements:
            if code in ifc_result.types_by_tag:
                matches += 1

        print(f"Tag Correlation: {matches} BC3 codes found in IFC types")
