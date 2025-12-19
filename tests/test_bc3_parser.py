"""Tests for BC3 Parser."""

import pytest
from pathlib import Path
import tempfile

from src.parsers.bc3_parser import BC3Parser, BC3Element, BC3ParseResult


class TestBC3Element:
    """Tests for BC3Element dataclass."""

    def test_create_basic_element(self):
        """Test creating a basic BC3 element."""
        elem = BC3Element(
            code="350147",
            unit="m3",
            description="Pilar rectangular hormigón - 600 x 600 mm",
            price=150.0
        )
        assert elem.code == "350147"
        assert elem.unit == "m3"
        assert elem.description == "Pilar rectangular hormigón - 600 x 600 mm"
        assert elem.price == 150.0
        assert elem.properties == {}
        assert elem.children == []

    def test_element_with_ifc_guid(self):
        """Test element with IFC GUID."""
        elem = BC3Element(
            code="350147",
            unit="m3",
            description="Test",
            price=0,
            type_ifc_guid="2yt6D8WIv1pOA$7fKuaiRG",
            family_name="Pilar rectangular hormigón",
            type_name="600 x 600 mm"
        )
        assert elem.type_ifc_guid == "2yt6D8WIv1pOA$7fKuaiRG"
        assert elem.family_name == "Pilar rectangular hormigón"
        assert elem.type_name == "600 x 600 mm"


class TestBC3Parser:
    """Tests for BC3Parser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return BC3Parser()

    @pytest.fixture
    def sample_bc3_content(self):
        """Sample BC3 content for testing."""
        return """~V|RIB Spain|FIEBDC-3/2020|Presto 25.01||ANSI||2||||
~C|350147|m3|Pilar rectangular hormigón - 600 x 600 mm|150.50|181225|0|
~X|350147|Tipo IfcGUID\\2yt6D8WIv1pOA$7fKuaiRG\\Nombre de familia\\Pilar rectangular hormigón\\Nombre de tipo\\600 x 600 mm\\h\\0.6\\b\\0.6\\|
~C|352900|m|JACENA I - I-220|0|181225|0|
~X|352900|Tipo IfcGUID\\2yt6D8WIv1pOA$7fKualEN\\Nombre de familia\\JACENA I\\Nombre de tipo\\I-220\\ALTURA JÁCENA\\1.2\\ANCHURA JÁCENA\\0.4\\|
~C|349637#||Pilar rectangular hormigón|0|181225|0|
~D|349637#|350147\\1\\63.62\\|
"""

    @pytest.fixture
    def temp_bc3_file(self, sample_bc3_content):
        """Create a temporary BC3 file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bc3', delete=False, encoding='latin-1') as f:
            f.write(sample_bc3_content)
            return Path(f.name)

    def test_parse_version(self, parser, temp_bc3_file):
        """Test parsing version info."""
        result = parser.parse(temp_bc3_file)
        assert "FIEBDC-3/2020" in result.version

    def test_parse_component(self, parser, temp_bc3_file):
        """Test parsing component records."""
        result = parser.parse(temp_bc3_file)

        assert "350147" in result.elements
        elem = result.elements["350147"]
        assert elem.code == "350147"
        assert elem.unit == "m3"
        assert "Pilar" in elem.description
        assert elem.price == 150.50

    def test_parse_extended_properties(self, parser, temp_bc3_file):
        """Test parsing extended properties including IFC GUID."""
        result = parser.parse(temp_bc3_file)

        elem = result.elements["350147"]
        assert elem.type_ifc_guid == "2yt6D8WIv1pOA$7fKuaiRG"
        assert elem.family_name == "Pilar rectangular hormigón"
        assert elem.type_name == "600 x 600 mm"
        assert elem.properties.get("h") == 0.6
        assert elem.properties.get("b") == 0.6

    def test_parse_beam_element(self, parser, temp_bc3_file):
        """Test parsing beam element with different properties."""
        result = parser.parse(temp_bc3_file)

        elem = result.elements["352900"]
        assert elem.type_ifc_guid == "2yt6D8WIv1pOA$7fKualEN"
        assert elem.family_name == "JACENA I"
        assert elem.type_name == "I-220"

    def test_parse_decomposition(self, parser, temp_bc3_file):
        """Test parsing decomposition/hierarchy."""
        result = parser.parse(temp_bc3_file)

        assert "349637" in result.hierarchy
        children = result.hierarchy["349637"]
        assert len(children) == 1
        assert children[0][0] == "350147"
        assert children[0][1] == 63.62

    def test_hierarchy_linking(self, parser, temp_bc3_file):
        """Test that hierarchy is linked to elements."""
        result = parser.parse(temp_bc3_file)

        parent = result.elements["349637"]
        assert len(parent.children) == 1
        assert parent.children[0][0] == "350147"

        child = result.elements["350147"]
        assert child.parent_code == "349637"
        assert child.quantity == 63.62

    def test_get_types_with_guid(self, parser, temp_bc3_file):
        """Test filtering elements with IFC GUID."""
        result = parser.parse(temp_bc3_file)
        types_with_guid = parser.get_types_with_guid(result)

        assert "350147" in types_with_guid
        assert "352900" in types_with_guid
        assert "349637" not in types_with_guid  # No GUID for parent

    def test_file_not_found(self, parser):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/file.bc3")

    def test_empty_file(self, parser):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bc3', delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        result = parser.parse(temp_path)
        assert len(result.elements) == 0

    def test_malformed_records(self, parser):
        """Test handling of malformed records."""
        content = """~V|Test|
~C|incomplete
~C||no_code||
~X|nonexistent_code|prop\\value\\|
~C|valid|m2|Valid Element|100|
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bc3', delete=False, encoding='latin-1') as f:
            f.write(content)
            temp_path = Path(f.name)

        result = parser.parse(temp_path)
        # Should still parse the valid element
        assert "valid" in result.elements


class TestBC3ParserWithRealFile:
    """Tests using the real BC3 file from the project."""

    @pytest.fixture
    def real_bc3_path(self):
        """Path to the real BC3 file."""
        path = Path(__file__).parent.parent / "data" / "input" / "GUIA MODELADO V2 2025-12-18 06-47-01.bc3"
        if not path.exists():
            pytest.skip(f"Real BC3 file not found: {path}")
        return path

    @pytest.fixture
    def parser(self):
        return BC3Parser()

    def test_parse_real_file(self, parser, real_bc3_path):
        """Test parsing the real BC3 file."""
        result = parser.parse(real_bc3_path)

        assert len(result.elements) > 0
        assert result.version != ""
        print(f"Parsed {len(result.elements)} elements")

    def test_real_file_has_ifc_guids(self, parser, real_bc3_path):
        """Test that real file contains IFC GUIDs."""
        result = parser.parse(real_bc3_path)
        types_with_guid = parser.get_types_with_guid(result)

        assert len(types_with_guid) > 0
        print(f"Found {len(types_with_guid)} elements with IFC GUID")

    def test_real_file_column_example(self, parser, real_bc3_path):
        """Test specific known element from the real file."""
        result = parser.parse(real_bc3_path)

        # Check for the column element we analyzed earlier
        if "350147" in result.elements:
            elem = result.elements["350147"]
            assert elem.family_name is not None
            assert elem.type_ifc_guid is not None
            print(f"Column element: {elem.family_name} - {elem.type_name}")
            print(f"  IFC GUID: {elem.type_ifc_guid}")

    def test_real_file_beam_example(self, parser, real_bc3_path):
        """Test beam element from the real file."""
        result = parser.parse(real_bc3_path)

        if "352900" in result.elements:
            elem = result.elements["352900"]
            assert elem.type_ifc_guid == "2yt6D8WIv1pOA$7fKualEN"
            assert elem.family_name == "JACENA I"
            print(f"Beam element: {elem.family_name} - {elem.type_name}")
