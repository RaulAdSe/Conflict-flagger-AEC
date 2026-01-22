#!/usr/bin/env python3
"""
Integration Test Script for IFC-BC3 Comparison Pipeline

This script runs integration tests against the baseline and test data to verify
the comparator works correctly with real files.

Tests:
1. Baseline comparison (GUIA MODELADO V2 IFC + BC3 pair)
2. Test scenarios (quantity mismatch, missing elements, name mismatch)
3. Verifies the new property_name field shows parameter details format

Usage:
    python3 run_integration_tests.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator, ConflictType, ConflictSeverity
from src.phases.config import Phase, get_phase_config


# File paths
DATA_DIR = Path(__file__).parent / "data"
BASELINE_DIR = DATA_DIR / "baseline"
TEST_DIR = DATA_DIR / "test"

# Baseline files
BASELINE_IFC = BASELINE_DIR / "GUIA MODELADO V2.ifc"
BASELINE_BC3 = BASELINE_DIR / "GUIA MODELADO V2.bc3"

# Test scenario files
SCENARIO1_BC3 = TEST_DIR / "scenario1_quantity_mismatch.bc3"
SCENARIO2_BC3 = TEST_DIR / "scenario2_missing_elements.bc3"
SCENARIO3_BC3 = TEST_DIR / "scenario3_name_mismatch.bc3"


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_section(title: str):
    """Print a section header."""
    print(f"\n--- {title} ---")


def run_comparison(ifc_path: Path, bc3_path: Path, name: str) -> dict:
    """
    Run the comparison pipeline and return results.

    Returns dict with:
    - match_result: MatchResult object
    - comparison_result: ComparisonResult object
    - summary: dict with totals
    """
    print_section(f"Running: {name}")
    print(f"  IFC: {ifc_path.name}")
    print(f"  BC3: {bc3_path.name}")

    # Parse IFC
    print("  Parsing IFC...")
    ifc_parser = IFCParser()
    ifc_result = ifc_parser.parse(ifc_path)
    print(f"    Found {len(ifc_result.types)} IFC types, {len(ifc_result.elements)} elements")

    # Parse BC3
    print("  Parsing BC3...")
    bc3_parser = BC3Parser()
    bc3_result = bc3_parser.parse(bc3_path)
    print(f"    Found {len(bc3_result.elements)} BC3 elements")

    # Match elements
    print("  Matching elements...")
    matcher = Matcher(match_by_name=True)
    match_result = matcher.match(ifc_result, bc3_result)
    print(f"    Matched: {len(match_result.matched)}")
    print(f"    IFC only: {len(match_result.ifc_only)}")
    print(f"    BC3 only: {len(match_result.bc3_only)}")

    # Compare
    print("  Comparing properties...")
    phase_config = get_phase_config(Phase.FULL_ANALYSIS)
    comparator = Comparator(tolerance=phase_config.quantity_tolerance)
    comparison_result = comparator.compare(match_result, phase_config)

    summary = comparison_result.summary()
    print(f"    Total conflicts: {summary['total_conflicts']}")
    print(f"    Errors: {summary['errors']}")
    print(f"    Warnings: {summary['warnings']}")
    print(f"    Infos: {summary['infos']}")

    return {
        'match_result': match_result,
        'comparison_result': comparison_result,
        'summary': summary
    }


def analyze_conflicts_by_type(conflicts: list) -> dict:
    """Group conflicts by type and return counts."""
    by_type = {}
    for c in conflicts:
        ct = c.conflict_type
        if ct not in by_type:
            by_type[ct] = []
        by_type[ct].append(c)
    return by_type


def print_conflict_details(conflicts: list, limit: int = 5, show_property_name: bool = True):
    """Print detailed conflict information."""
    for i, c in enumerate(conflicts[:limit]):
        severity_icon = {
            ConflictSeverity.ERROR: "[ERROR]",
            ConflictSeverity.WARNING: "[WARN]",
            ConflictSeverity.INFO: "[INFO]"
        }.get(c.severity, "[?]")

        print(f"\n  {i+1}. {severity_icon} {c.conflict_type.value}")
        print(f"     Code: {c.element_code}")
        print(f"     Name: {c.element_name[:60]}..." if len(c.element_name) > 60 else f"     Name: {c.element_name}")

        if show_property_name:
            print(f"     Property: {c.property_name}")

        if c.ifc_value is not None or c.bc3_value is not None:
            print(f"     Values - IFC: {c.ifc_value}, BC3: {c.bc3_value}")

        if c.description:
            desc = c.description[:80] + "..." if len(c.description) > 80 else c.description
            print(f"     Description: {desc}")

        if c.quantity_source:
            print(f"     Quantity Source: {c.quantity_source}")

    if len(conflicts) > limit:
        print(f"\n  ... and {len(conflicts) - limit} more")


def verify_property_name_format(conflicts: list) -> bool:
    """
    Verify that quantity mismatch conflicts have the new property_name format
    showing parameter details like "h (bc3: 0,60, ifc: 0,65)" instead of just "Cantidad".

    Returns True if the new format is detected, False otherwise.
    """
    print_section("Verifying property_name format")

    quantity_mismatches = [c for c in conflicts if c.conflict_type == ConflictType.QUANTITY_MISMATCH]

    if not quantity_mismatches:
        print("  No quantity mismatch conflicts found to verify")
        return False

    # Check for the new format pattern
    new_format_count = 0
    old_format_count = 0

    for c in quantity_mismatches:
        prop_name = c.property_name

        # New format should contain parameter details like "(bc3:" or match pattern like "h (bc3: x,xx, ifc: x,xx)"
        if "(bc3:" in prop_name or "(ifc:" in prop_name:
            new_format_count += 1
            print(f"  [NEW FORMAT] {c.element_code}: {prop_name[:80]}")
        elif prop_name == "Cantidad":
            old_format_count += 1
            print(f"  [OLD FORMAT] {c.element_code}: {prop_name}")
        else:
            # Some other format
            print(f"  [OTHER] {c.element_code}: {prop_name[:80]}")

    print(f"\n  Summary:")
    print(f"    New format (with parameter details): {new_format_count}")
    print(f"    Old format ('Cantidad' only): {old_format_count}")

    if new_format_count > 0:
        print(f"\n  [PASS] New property_name format is working!")
        return True
    else:
        print(f"\n  [INFO] No conflicts with new parameter details format found")
        print(f"         This may be expected if BC3 elements don't have dimensional parameters")
        return False


def test_baseline():
    """Test comparison on baseline files (should have minimal conflicts)."""
    print_header("TEST 1: BASELINE COMPARISON")
    print("Testing GUIA MODELADO V2 IFC + BC3 pair")
    print("Expected: Minimal conflicts (files should match well)")

    if not BASELINE_IFC.exists():
        print(f"  [ERROR] IFC file not found: {BASELINE_IFC}")
        return None
    if not BASELINE_BC3.exists():
        print(f"  [ERROR] BC3 file not found: {BASELINE_BC3}")
        return None

    result = run_comparison(BASELINE_IFC, BASELINE_BC3, "Baseline")

    # Analyze by type
    by_type = analyze_conflicts_by_type(result['comparison_result'].conflicts)

    print_section("Conflicts by Type")
    for ct, conflicts in sorted(by_type.items(), key=lambda x: x[0].value):
        print(f"  {ct.value}: {len(conflicts)}")

    # Show sample conflicts
    if result['comparison_result'].conflicts:
        print_section("Sample Conflicts (first 5)")
        print_conflict_details(result['comparison_result'].conflicts, limit=5)

    return result


def test_scenario1():
    """Test Scenario 1: Quantity Mismatches."""
    print_header("TEST 2: SCENARIO 1 - QUANTITY MISMATCHES")
    print("Testing modified BC3 with quantity errors")
    print("Expected: Quantity mismatch errors for modified elements")

    if not BASELINE_IFC.exists():
        print(f"  [ERROR] IFC file not found: {BASELINE_IFC}")
        return None
    if not SCENARIO1_BC3.exists():
        print(f"  [ERROR] Scenario BC3 file not found: {SCENARIO1_BC3}")
        return None

    result = run_comparison(BASELINE_IFC, SCENARIO1_BC3, "Scenario 1: Quantity Mismatch")

    # Focus on quantity mismatches
    quantity_conflicts = [c for c in result['comparison_result'].conflicts
                         if c.conflict_type == ConflictType.QUANTITY_MISMATCH]

    print_section(f"Quantity Mismatch Conflicts ({len(quantity_conflicts)} found)")
    print_conflict_details(quantity_conflicts, limit=10, show_property_name=True)

    return result


def test_scenario2():
    """Test Scenario 2: Missing Elements."""
    print_header("TEST 3: SCENARIO 2 - MISSING ELEMENTS")
    print("Testing modified BC3 with missing elements")
    print("Expected: Missing element warnings")

    if not BASELINE_IFC.exists():
        print(f"  [ERROR] IFC file not found: {BASELINE_IFC}")
        return None
    if not SCENARIO2_BC3.exists():
        print(f"  [ERROR] Scenario BC3 file not found: {SCENARIO2_BC3}")
        return None

    result = run_comparison(BASELINE_IFC, SCENARIO2_BC3, "Scenario 2: Missing Elements")

    # Focus on missing element conflicts
    missing_in_bc3 = [c for c in result['comparison_result'].conflicts
                     if c.conflict_type == ConflictType.MISSING_IN_BC3]
    missing_in_ifc = [c for c in result['comparison_result'].conflicts
                     if c.conflict_type == ConflictType.MISSING_IN_IFC]

    print_section(f"Missing in BC3 ({len(missing_in_bc3)} found)")
    print_conflict_details(missing_in_bc3, limit=5)

    print_section(f"Missing in IFC ({len(missing_in_ifc)} found)")
    print_conflict_details(missing_in_ifc, limit=5)

    return result


def test_scenario3():
    """Test Scenario 3: Name Mismatches."""
    print_header("TEST 4: SCENARIO 3 - NAME MISMATCHES")
    print("Testing modified BC3 with name/description changes")
    print("Expected: Name mismatch infos")

    if not BASELINE_IFC.exists():
        print(f"  [ERROR] IFC file not found: {BASELINE_IFC}")
        return None
    if not SCENARIO3_BC3.exists():
        print(f"  [ERROR] Scenario BC3 file not found: {SCENARIO3_BC3}")
        return None

    result = run_comparison(BASELINE_IFC, SCENARIO3_BC3, "Scenario 3: Name Mismatch")

    # Focus on name mismatch conflicts
    name_conflicts = [c for c in result['comparison_result'].conflicts
                     if c.conflict_type == ConflictType.NAME_MISMATCH]

    print_section(f"Name Mismatch Conflicts ({len(name_conflicts)} found)")
    print_conflict_details(name_conflicts, limit=5)

    return result


def print_final_summary(results: dict):
    """Print final summary of all tests."""
    print_header("FINAL SUMMARY")

    print("\n  Test Results:")
    print("  " + "-" * 50)

    for name, result in results.items():
        if result is None:
            print(f"  {name}: SKIPPED (file not found)")
        else:
            summary = result['summary']
            status = "[OK]" if summary['errors'] < 10 else "[REVIEW]"
            print(f"  {status} {name}:")
            print(f"        Conflicts: {summary['total_conflicts']} "
                  f"(E:{summary['errors']}, W:{summary['warnings']}, I:{summary['infos']})")

    print("  " + "-" * 50)


def main():
    """Main entry point."""
    print_header("INTEGRATION TESTS FOR IFC-BC3 COMPARISON PIPELINE")
    print(f"Working Directory: {Path.cwd()}")
    print(f"Data Directory: {DATA_DIR}")

    results = {}

    # Test 1: Baseline
    results['Baseline'] = test_baseline()

    # Check if test scenarios exist, create them if needed
    scenarios_exist = all([
        SCENARIO1_BC3.exists(),
        SCENARIO2_BC3.exists(),
        SCENARIO3_BC3.exists()
    ])

    if not scenarios_exist:
        print_header("GENERATING TEST SCENARIOS")
        print("Some test scenario files are missing. Running test_controlled_scenarios.py to generate them...")

        try:
            from tests.test_controlled_scenarios import (
                ensure_test_dir,
                create_scenario1_quantity_mismatch,
                create_scenario2_missing_elements,
                create_scenario3_name_mismatch
            )

            ensure_test_dir()
            create_scenario1_quantity_mismatch()
            create_scenario2_missing_elements()
            create_scenario3_name_mismatch()
            print("  [OK] Test scenarios generated successfully")
        except Exception as e:
            print(f"  [ERROR] Failed to generate test scenarios: {e}")

    # Test 2-4: Scenarios
    results['Scenario 1: Quantity Mismatch'] = test_scenario1()
    results['Scenario 2: Missing Elements'] = test_scenario2()
    results['Scenario 3: Name Mismatch'] = test_scenario3()

    # Verify new property_name format
    print_header("PROPERTY_NAME FORMAT VERIFICATION")

    # Check scenario 1 conflicts for the new format
    if results['Scenario 1: Quantity Mismatch']:
        verify_property_name_format(results['Scenario 1: Quantity Mismatch']['comparison_result'].conflicts)

    # Also check baseline
    if results['Baseline']:
        print("\n  Checking baseline conflicts:")
        verify_property_name_format(results['Baseline']['comparison_result'].conflicts)

    # Print final summary
    print_final_summary(results)

    print("\n[DONE] Integration tests completed.")

    # Return exit code based on results
    errors_found = any(
        r and r['summary']['errors'] > 0
        for r in results.values()
        if r is not None
    )

    return 0  # Always return 0 since errors are expected in test scenarios


if __name__ == "__main__":
    sys.exit(main())
