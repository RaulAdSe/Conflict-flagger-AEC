"""
Test Data Generator

Creates modified versions of BC3 and IFC files for testing conflict detection.
Generates various test scenarios: missing elements, property mismatches, orphan elements, etc.
"""

import re
import shutil
from pathlib import Path
from typing import Optional

import ifcopenshell


class BC3Modifier:
    """Modifies BC3 files to create test scenarios."""

    def __init__(self, source_path: str | Path):
        """
        Initialize with a source BC3 file.

        Args:
            source_path: Path to the original BC3 file
        """
        self.source_path = Path(source_path)
        self.content = self._read_file()
        self.lines = self.content.split('\n')

    def _read_file(self) -> str:
        """Read the source file."""
        return self.source_path.read_text(encoding='latin-1', errors='replace')

    def remove_elements(self, codes: list[str]) -> 'BC3Modifier':
        """
        Remove elements by their codes.

        Args:
            codes: List of element codes to remove
        """
        new_lines = []
        skip_until_next_record = False
        current_code = None

        for line in self.lines:
            # Check if this is a record for a code we want to remove
            match = re.match(r'^~[A-Z]\|([^|#]+)#?\|', line)
            if match:
                current_code = match.group(1).rstrip('#')
                if current_code in codes:
                    skip_until_next_record = True
                    continue
                else:
                    skip_until_next_record = False

            if not skip_until_next_record:
                new_lines.append(line)

        self.lines = new_lines
        self.content = '\n'.join(self.lines)
        return self

    def modify_property(self, code: str, property_name: str, new_value: str) -> 'BC3Modifier':
        """
        Modify a property value in an ~X record.

        Args:
            code: Element code
            property_name: Name of property to modify
            new_value: New value for the property
        """
        new_lines = []
        for line in self.lines:
            if line.startswith(f'~X|{code}|'):
                # Find and replace the property
                pattern = rf'({re.escape(property_name)}\\)[^\\]*(\\)'
                replacement = rf'\g<1>{new_value}\g<2>'
                line = re.sub(pattern, replacement, line)
            new_lines.append(line)

        self.lines = new_lines
        self.content = '\n'.join(self.lines)
        return self

    def add_orphan_element(self, code: str, unit: str, description: str, price: float) -> 'BC3Modifier':
        """
        Add a new element that won't exist in IFC.

        Args:
            code: New element code
            unit: Unit of measurement
            description: Element description
            price: Element price
        """
        new_line = f"~C|{code}|{unit}|{description}|{price}|999999|0|"
        self.lines.append(new_line)
        self.content = '\n'.join(self.lines)
        return self

    def change_description(self, code: str, new_description: str) -> 'BC3Modifier':
        """
        Change the description of an element.

        Args:
            code: Element code
            new_description: New description
        """
        new_lines = []
        for line in self.lines:
            if line.startswith(f'~C|{code}|') or line.startswith(f'~C|{code}#|'):
                parts = line.split('|')
                if len(parts) >= 4:
                    parts[3] = new_description
                    line = '|'.join(parts)
            new_lines.append(line)

        self.lines = new_lines
        self.content = '\n'.join(self.lines)
        return self

    def save(self, output_path: str | Path) -> Path:
        """
        Save the modified BC3 file.

        Args:
            output_path: Path for the output file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.content, encoding='latin-1')
        return output_path


class IFCModifier:
    """Modifies IFC files to create test scenarios."""

    def __init__(self, source_path: str | Path):
        """
        Initialize with a source IFC file.

        Args:
            source_path: Path to the original IFC file
        """
        self.source_path = Path(source_path)
        self.ifc_file = ifcopenshell.open(str(self.source_path))
        self.removed_elements = []
        self.modified_properties = []

    def get_elements_by_class(self, ifc_class: str) -> list:
        """Get all elements of a specific IFC class."""
        try:
            return list(self.ifc_file.by_type(ifc_class))
        except RuntimeError:
            return []

    def get_element_by_tag(self, tag: str):
        """Get an element by its Tag attribute."""
        for element in self.ifc_file.by_type('IfcBuildingElement'):
            try:
                if hasattr(element, 'Tag') and element.Tag == tag:
                    return element
            except Exception:
                continue
        return None

    def remove_elements_by_tags(self, tags: list[str]) -> 'IFCModifier':
        """
        Remove elements by their tags.

        Args:
            tags: List of element tags to remove
        """
        for tag in tags:
            element = self.get_element_by_tag(tag)
            if element:
                self.ifc_file.remove(element)
                self.removed_elements.append(tag)
        return self

    def remove_elements_by_class(self, ifc_class: str, count: int = 1) -> 'IFCModifier':
        """
        Remove a number of elements of a specific class.

        Args:
            ifc_class: IFC class to remove (e.g., 'IfcColumn', 'IfcBeam')
            count: Number of elements to remove
        """
        elements = self.get_elements_by_class(ifc_class)
        for element in elements[:count]:
            tag = getattr(element, 'Tag', None) or element.GlobalId
            self.ifc_file.remove(element)
            self.removed_elements.append(f"{ifc_class}:{tag}")
        return self

    def modify_element_property(self, tag: str, property_name: str, new_value) -> 'IFCModifier':
        """
        Modify a property value of an element.

        Args:
            tag: Element tag
            property_name: Name of property to modify
            new_value: New value for the property
        """
        element = self.get_element_by_tag(tag)
        if element and hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a('IfcPropertySet'):
                        for prop in prop_set.HasProperties:
                            if prop.is_a('IfcPropertySingleValue') and prop.Name == property_name:
                                # Create new value
                                if isinstance(new_value, float):
                                    prop.NominalValue = self.ifc_file.createIfcLengthMeasure(new_value)
                                elif isinstance(new_value, str):
                                    prop.NominalValue = self.ifc_file.createIfcLabel(new_value)
                                self.modified_properties.append(f"{tag}:{property_name}={new_value}")
        return self

    def modify_element_name(self, tag: str, new_name: str) -> 'IFCModifier':
        """
        Modify the name of an element.

        Args:
            tag: Element tag
            new_name: New name for the element
        """
        element = self.get_element_by_tag(tag)
        if element:
            element.Name = new_name
            self.modified_properties.append(f"{tag}:Name={new_name}")
        return self

    def add_dummy_element(self, ifc_class: str = 'IfcBuildingElementProxy',
                          name: str = 'DUMMY_ELEMENT',
                          tag: str = 'DUMMY001') -> 'IFCModifier':
        """
        Add a dummy element that won't exist in BC3.

        Args:
            ifc_class: Type of element to create
            name: Name for the element
            tag: Tag for the element
        """
        # Create owner history reference
        owner_history = self.ifc_file.by_type('IfcOwnerHistory')[0] if self.ifc_file.by_type('IfcOwnerHistory') else None

        # Generate a new GlobalId
        import uuid
        global_id = ifcopenshell.guid.compress(uuid.uuid4().hex)

        # Create a simple building element proxy
        element = self.ifc_file.create_entity(
            ifc_class,
            GlobalId=global_id,
            OwnerHistory=owner_history,
            Name=name,
            Tag=tag
        )
        return self

    def save(self, output_path: str | Path) -> Path:
        """
        Save the modified IFC file.

        Args:
            output_path: Path for the output file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.ifc_file.write(str(output_path))
        return output_path


def create_bc3_variants(source_bc3: str | Path, output_dir: str | Path) -> dict:
    """
    Create multiple test variants of a BC3 file.

    Args:
        source_bc3: Path to the original BC3 file
        output_dir: Directory for output files

    Returns:
        Dictionary mapping variant name to file path
    """
    source_bc3 = Path(source_bc3)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = {}

    # Variant 1: Removed elements (simulates elements not budgeted)
    print("Creating variant: elements_removed...")
    modifier = BC3Modifier(source_bc3)
    modifier.remove_elements(['350147', '352900', '350145'])  # Remove some columns and beams
    path = modifier.save(output_dir / "bc3_elements_removed.bc3")
    variants['elements_removed'] = path
    print(f"  Saved to: {path}")

    # Variant 2: Modified properties (simulates property mismatches)
    print("Creating variant: properties_modified...")
    modifier = BC3Modifier(source_bc3)
    modifier.modify_property('350147', 'h', '0.8')  # Change height from 0.6 to 0.8
    modifier.modify_property('350147', 'b', '0.8')  # Change width from 0.6 to 0.8
    modifier.modify_property('352900', 'ALTURA JÁCENA', '2.0')  # Change beam height
    path = modifier.save(output_dir / "bc3_properties_modified.bc3")
    variants['properties_modified'] = path
    print(f"  Saved to: {path}")

    # Variant 3: Added orphan elements (simulates budget items without model)
    print("Creating variant: orphan_elements...")
    modifier = BC3Modifier(source_bc3)
    modifier.add_orphan_element('ORPHAN001', 'm2', 'Orphan Wall - Not in model', 150.0)
    modifier.add_orphan_element('ORPHAN002', 'u', 'Orphan Door - Not in model', 500.0)
    modifier.add_orphan_element('ORPHAN003', 'm3', 'Orphan Foundation - Not in model', 200.0)
    path = modifier.save(output_dir / "bc3_orphan_elements.bc3")
    variants['orphan_elements'] = path
    print(f"  Saved to: {path}")

    # Variant 4: Combined issues (realistic scenario)
    print("Creating variant: combined_issues...")
    modifier = BC3Modifier(source_bc3)
    modifier.remove_elements(['360466', '361849'])  # Remove some elements
    modifier.modify_property('350147', 'h', '0.7')  # Slight dimension change
    modifier.add_orphan_element('BUDGET_EXTRA', 'm2', 'Extra budget item', 100.0)
    path = modifier.save(output_dir / "bc3_combined_issues.bc3")
    variants['combined_issues'] = path
    print(f"  Saved to: {path}")

    # Variant 5: Identical (for baseline testing - no changes)
    print("Creating variant: identical...")
    modifier = BC3Modifier(source_bc3)
    path = modifier.save(output_dir / "bc3_identical.bc3")
    variants['identical'] = path
    print(f"  Saved to: {path}")

    return variants


def create_ifc_variants(source_ifc: str | Path, output_dir: str | Path) -> dict:
    """
    Create multiple test variants of an IFC file.

    Args:
        source_ifc: Path to the original IFC file
        output_dir: Directory for output files

    Returns:
        Dictionary mapping variant name to file path
    """
    source_ifc = Path(source_ifc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = {}

    # First, get some element info from the source file
    print("Analyzing source IFC file...")
    source_model = ifcopenshell.open(str(source_ifc))
    columns = list(source_model.by_type('IfcColumn'))
    beams = list(source_model.by_type('IfcBeam'))
    print(f"  Found {len(columns)} columns and {len(beams)} beams")

    # Get some element tags to use in modifications
    column_tags = [c.Tag for c in columns[:5] if hasattr(c, 'Tag') and c.Tag]
    beam_tags = [b.Tag for b in beams[:5] if hasattr(b, 'Tag') and b.Tag]
    print(f"  Sample column tags: {column_tags[:3]}")
    print(f"  Sample beam tags: {beam_tags[:3]}")

    # Variant 1: Removed columns (simulates model elements not in budget)
    print("\nCreating IFC variant: columns_removed...")
    modifier = IFCModifier(source_ifc)
    modifier.remove_elements_by_class('IfcColumn', count=3)
    path = modifier.save(output_dir / "ifc_columns_removed.ifc")
    variants['columns_removed'] = path
    print(f"  Removed elements: {modifier.removed_elements}")
    print(f"  Saved to: {path}")

    # Variant 2: Removed beams
    print("\nCreating IFC variant: beams_removed...")
    modifier = IFCModifier(source_ifc)
    modifier.remove_elements_by_class('IfcBeam', count=3)
    path = modifier.save(output_dir / "ifc_beams_removed.ifc")
    variants['beams_removed'] = path
    print(f"  Removed elements: {modifier.removed_elements}")
    print(f"  Saved to: {path}")

    # Variant 3: Added orphan elements (model elements without budget)
    print("\nCreating IFC variant: orphan_elements...")
    modifier = IFCModifier(source_ifc)
    modifier.add_dummy_element('IfcBuildingElementProxy', 'IFC_ORPHAN_1', 'IFC_ORPHAN001')
    modifier.add_dummy_element('IfcBuildingElementProxy', 'IFC_ORPHAN_2', 'IFC_ORPHAN002')
    modifier.add_dummy_element('IfcBuildingElementProxy', 'IFC_ORPHAN_3', 'IFC_ORPHAN003')
    path = modifier.save(output_dir / "ifc_orphan_elements.ifc")
    variants['orphan_elements'] = path
    print(f"  Saved to: {path}")

    # Variant 4: Combined issues
    print("\nCreating IFC variant: combined_issues...")
    modifier = IFCModifier(source_ifc)
    modifier.remove_elements_by_class('IfcColumn', count=2)
    modifier.remove_elements_by_class('IfcBeam', count=1)
    modifier.add_dummy_element('IfcBuildingElementProxy', 'EXTRA_IFC_ELEMENT', 'EXTRA001')
    path = modifier.save(output_dir / "ifc_combined_issues.ifc")
    variants['combined_issues'] = path
    print(f"  Removed elements: {modifier.removed_elements}")
    print(f"  Saved to: {path}")

    # Variant 5: Identical (for baseline testing - just copy)
    print("\nCreating IFC variant: identical...")
    path = output_dir / "ifc_identical.ifc"
    shutil.copy(source_ifc, path)
    variants['identical'] = path
    print(f"  Saved to: {path}")

    return variants


def create_test_scenarios(source_bc3: str | Path, source_ifc: str | Path,
                          output_dir: str | Path) -> dict:
    """
    Create comprehensive test scenarios with matched BC3/IFC modifications.

    Args:
        source_bc3: Path to the original BC3 file
        source_ifc: Path to the original IFC file
        output_dir: Directory for output files

    Returns:
        Dictionary mapping scenario name to (bc3_path, ifc_path) tuple
    """
    source_bc3 = Path(source_bc3)
    source_ifc = Path(source_ifc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = {}

    print("=" * 60)
    print("CREATING COMPREHENSIVE TEST SCENARIOS")
    print("=" * 60)

    # Scenario 1: Baseline - identical files
    print("\n[Scenario 1] Baseline (identical files)")
    bc3_path = output_dir / "scenario_baseline.bc3"
    ifc_path = output_dir / "scenario_baseline.ifc"
    BC3Modifier(source_bc3).save(bc3_path)
    shutil.copy(source_ifc, ifc_path)
    scenarios['baseline'] = {'bc3': bc3_path, 'ifc': ifc_path, 'description': 'Identical files - no conflicts expected'}
    print(f"  BC3: {bc3_path}")
    print(f"  IFC: {ifc_path}")

    # Scenario 2: BC3 missing elements (budget didn't include some IFC elements)
    print("\n[Scenario 2] BC3 Missing Elements")
    bc3_mod = BC3Modifier(source_bc3)
    bc3_mod.remove_elements(['350147', '352900', '350145', '360466'])
    bc3_path = output_dir / "scenario_bc3_missing.bc3"
    ifc_path = output_dir / "scenario_bc3_missing.ifc"
    bc3_mod.save(bc3_path)
    shutil.copy(source_ifc, ifc_path)
    scenarios['bc3_missing'] = {'bc3': bc3_path, 'ifc': ifc_path, 'description': 'BC3 missing 4 elements that exist in IFC'}
    print(f"  BC3: {bc3_path} (removed 4 elements)")
    print(f"  IFC: {ifc_path}")

    # Scenario 3: IFC missing elements (model didn't include budgeted items)
    print("\n[Scenario 3] IFC Missing Elements")
    bc3_path = output_dir / "scenario_ifc_missing.bc3"
    ifc_path = output_dir / "scenario_ifc_missing.ifc"
    BC3Modifier(source_bc3).save(bc3_path)
    ifc_mod = IFCModifier(source_ifc)
    ifc_mod.remove_elements_by_class('IfcColumn', count=4)
    ifc_mod.save(ifc_path)
    scenarios['ifc_missing'] = {'bc3': bc3_path, 'ifc': ifc_path,
                                 'description': f'IFC missing elements: {ifc_mod.removed_elements}'}
    print(f"  BC3: {bc3_path}")
    print(f"  IFC: {ifc_path} (removed {len(ifc_mod.removed_elements)} elements)")

    # Scenario 4: Property mismatches (dimensions differ)
    print("\n[Scenario 4] Property Mismatches")
    bc3_mod = BC3Modifier(source_bc3)
    bc3_mod.modify_property('350147', 'h', '0.8')
    bc3_mod.modify_property('350147', 'b', '0.8')
    bc3_mod.modify_property('352900', 'ALTURA JÁCENA', '2.0')
    bc3_path = output_dir / "scenario_property_mismatch.bc3"
    ifc_path = output_dir / "scenario_property_mismatch.ifc"
    bc3_mod.save(bc3_path)
    shutil.copy(source_ifc, ifc_path)
    scenarios['property_mismatch'] = {'bc3': bc3_path, 'ifc': ifc_path,
                                       'description': 'BC3 has modified property values (h, b, height)'}
    print(f"  BC3: {bc3_path} (modified properties)")
    print(f"  IFC: {ifc_path}")

    # Scenario 5: Orphan elements in BC3 (budget items without model representation)
    print("\n[Scenario 5] BC3 Orphan Elements")
    bc3_mod = BC3Modifier(source_bc3)
    bc3_mod.add_orphan_element('ORPHAN_WALL_001', 'm2', 'Muro exterior no modelado', 150.0)
    bc3_mod.add_orphan_element('ORPHAN_DOOR_001', 'u', 'Puerta adicional presupuestada', 500.0)
    bc3_mod.add_orphan_element('ORPHAN_FOUND_001', 'm3', 'Cimentación adicional', 200.0)
    bc3_path = output_dir / "scenario_bc3_orphans.bc3"
    ifc_path = output_dir / "scenario_bc3_orphans.ifc"
    bc3_mod.save(bc3_path)
    shutil.copy(source_ifc, ifc_path)
    scenarios['bc3_orphans'] = {'bc3': bc3_path, 'ifc': ifc_path,
                                 'description': 'BC3 has 3 orphan elements not in IFC'}
    print(f"  BC3: {bc3_path} (added 3 orphan elements)")
    print(f"  IFC: {ifc_path}")

    # Scenario 6: Orphan elements in IFC (model elements without budget)
    print("\n[Scenario 6] IFC Orphan Elements")
    bc3_path = output_dir / "scenario_ifc_orphans.bc3"
    ifc_path = output_dir / "scenario_ifc_orphans.ifc"
    BC3Modifier(source_bc3).save(bc3_path)
    ifc_mod = IFCModifier(source_ifc)
    ifc_mod.add_dummy_element('IfcBuildingElementProxy', 'Elemento sin presupuesto 1', 'NO_BUDGET_001')
    ifc_mod.add_dummy_element('IfcBuildingElementProxy', 'Elemento sin presupuesto 2', 'NO_BUDGET_002')
    ifc_mod.save(ifc_path)
    scenarios['ifc_orphans'] = {'bc3': bc3_path, 'ifc': ifc_path,
                                 'description': 'IFC has 2 orphan elements not in BC3'}
    print(f"  BC3: {bc3_path}")
    print(f"  IFC: {ifc_path} (added 2 orphan elements)")

    # Scenario 7: Combined issues (realistic scenario)
    print("\n[Scenario 7] Combined Issues (Realistic)")
    bc3_mod = BC3Modifier(source_bc3)
    bc3_mod.remove_elements(['360466', '361849'])
    bc3_mod.modify_property('350147', 'h', '0.7')
    bc3_mod.add_orphan_element('EXTRA_BUDGET', 'm2', 'Partida extra no modelada', 100.0)
    bc3_path = output_dir / "scenario_combined.bc3"
    ifc_path = output_dir / "scenario_combined.ifc"
    bc3_mod.save(bc3_path)
    ifc_mod = IFCModifier(source_ifc)
    ifc_mod.remove_elements_by_class('IfcBeam', count=2)
    ifc_mod.add_dummy_element('IfcBuildingElementProxy', 'Extra IFC element', 'EXTRA_IFC_001')
    ifc_mod.save(ifc_path)
    scenarios['combined'] = {'bc3': bc3_path, 'ifc': ifc_path,
                              'description': 'Multiple issues: missing, orphans, and property mismatches on both sides'}
    print(f"  BC3: {bc3_path} (removed 2, modified 1, added 1 orphan)")
    print(f"  IFC: {ifc_path} (removed 2, added 1 orphan)")

    # Scenario 8: Many missing elements (stress test)
    print("\n[Scenario 8] Stress Test - Many Missing")
    bc3_mod = BC3Modifier(source_bc3)
    # Remove more elements
    bc3_mod.remove_elements(['350147', '352900', '350145', '360466', '361849', '350148', '350149', '350150'])
    bc3_path = output_dir / "scenario_stress_test.bc3"
    ifc_path = output_dir / "scenario_stress_test.ifc"
    bc3_mod.save(bc3_path)
    ifc_mod = IFCModifier(source_ifc)
    ifc_mod.remove_elements_by_class('IfcColumn', count=5)
    ifc_mod.remove_elements_by_class('IfcBeam', count=5)
    ifc_mod.save(ifc_path)
    scenarios['stress_test'] = {'bc3': bc3_path, 'ifc': ifc_path,
                                 'description': 'Heavy modifications on both sides - stress test'}
    print(f"  BC3: {bc3_path} (removed many elements)")
    print(f"  IFC: {ifc_path} (removed {len(ifc_mod.removed_elements)} elements)")

    return scenarios


def main():
    """Main entry point for generating test data."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate BC3 and IFC test variants")
    parser.add_argument("--bc3", help="Source BC3 file",
                       default="data/input/GUIA MODELADO V2 2025-12-18 06-47-01.bc3")
    parser.add_argument("--ifc", help="Source IFC file",
                       default="data/input/GUIA MODELADO V2.ifc")
    parser.add_argument("--output-dir", "-o", default="data/test_variants",
                       help="Output directory for variants")
    parser.add_argument("--mode", choices=['bc3', 'ifc', 'scenarios', 'all'], default='scenarios',
                       help="What to generate: bc3 variants, ifc variants, scenarios, or all")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.mode in ['bc3', 'all']:
        source_bc3 = Path(args.bc3)
        if not source_bc3.exists():
            print(f"Error: BC3 file not found: {source_bc3}")
            return 1
        print(f"\n{'='*60}")
        print("GENERATING BC3 VARIANTS")
        print(f"{'='*60}")
        print(f"Source: {source_bc3}")
        variants = create_bc3_variants(source_bc3, output_dir / "bc3_variants")
        print(f"\nCreated {len(variants)} BC3 variants")

    if args.mode in ['ifc', 'all']:
        source_ifc = Path(args.ifc)
        if not source_ifc.exists():
            print(f"Error: IFC file not found: {source_ifc}")
            return 1
        print(f"\n{'='*60}")
        print("GENERATING IFC VARIANTS")
        print(f"{'='*60}")
        print(f"Source: {source_ifc}")
        variants = create_ifc_variants(source_ifc, output_dir / "ifc_variants")
        print(f"\nCreated {len(variants)} IFC variants")

    if args.mode in ['scenarios', 'all']:
        source_bc3 = Path(args.bc3)
        source_ifc = Path(args.ifc)
        if not source_bc3.exists():
            print(f"Error: BC3 file not found: {source_bc3}")
            return 1
        if not source_ifc.exists():
            print(f"Error: IFC file not found: {source_ifc}")
            return 1
        scenarios = create_test_scenarios(source_bc3, source_ifc, output_dir / "scenarios")
        print(f"\n{'='*60}")
        print(f"CREATED {len(scenarios)} TEST SCENARIOS")
        print(f"{'='*60}")
        for name, info in scenarios.items():
            print(f"\n{name}:")
            print(f"  Description: {info['description']}")
            print(f"  BC3: {info['bc3']}")
            print(f"  IFC: {info['ifc']}")

    print(f"\n\nAll test data saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
