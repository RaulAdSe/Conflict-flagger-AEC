"""
Test Data Generator

Creates modified versions of BC3 files for testing conflict detection.
Since IFC files are binary and complex, we modify BC3 files to simulate
different scenarios.
"""

import re
from pathlib import Path
from typing import Optional


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


def create_test_variants(source_bc3: str | Path, output_dir: str | Path) -> dict:
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


def main():
    """Main entry point for generating test data."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate BC3 test variants")
    parser.add_argument("source", help="Source BC3 file")
    parser.add_argument("--output-dir", "-o", default="data/test_variants",
                       help="Output directory for variants")

    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Error: Source file not found: {source}")
        return 1

    print(f"Source BC3: {source}")
    print(f"Output dir: {args.output_dir}")
    print()

    variants = create_test_variants(source, args.output_dir)

    print(f"\nCreated {len(variants)} test variants:")
    for name, path in variants.items():
        print(f"  - {name}: {path}")

    return 0


if __name__ == "__main__":
    exit(main())
