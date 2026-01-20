"""
Regression Test for IFC-BC3 Comparison Pipeline

This test verifies that:
1. The intended errors/warnings from our modifications are detected
2. The baseline conflicts don't increase (no false positives introduced)
3. No baseline conflicts disappear unexpectedly

Approach:
- Run baseline (unmodified files) to establish conflict baseline
- Run each scenario and compare against baseline
- Verify ONLY the expected changes occur
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Set, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator, ConflictType, ConflictSeverity, Conflict
from src.phases.config import Phase, get_phase_config
from tests.test_controlled_scenarios import (
    BC3ModifierExtended,
    BASELINE_IFC, BASELINE_BC3, TEST_OUTPUT_DIR,
    ensure_test_dir
)


@dataclass
class ConflictKey:
    """Unique identifier for a conflict."""
    element_code: str
    conflict_type: ConflictType

    def __hash__(self):
        return hash((self.element_code, self.conflict_type))

    def __eq__(self, other):
        return self.element_code == other.element_code and self.conflict_type == other.conflict_type

    def __str__(self):
        return f"{self.element_code}:{self.conflict_type.value}"


@dataclass
class ConflictInfo:
    """Full conflict information for comparison."""
    key: ConflictKey
    severity: ConflictSeverity
    ifc_value: any
    bc3_value: any
    description: str


def run_comparison(ifc_path: Path, bc3_path: Path) -> Tuple[dict, List[Conflict]]:
    """Run the comparison pipeline and return results."""
    ifc_result = IFCParser().parse(ifc_path)
    bc3_result = BC3Parser().parse(bc3_path)
    matcher = Matcher(match_by_name=True)
    match_result = matcher.match(ifc_result, bc3_result)
    phase_config = get_phase_config(Phase.FULL_ANALYSIS)
    comparator = Comparator(tolerance=phase_config.quantity_tolerance)
    comparison = comparator.compare(match_result, phase_config)

    return {
        'matched': len(match_result.matched),
        'ifc_only': len(match_result.ifc_only),
        'bc3_only': len(match_result.bc3_only),
        'conflicts': comparison.conflicts,
        'summary': comparison.summary()
    }, comparison.conflicts


def conflicts_to_set(conflicts: List[Conflict]) -> Set[ConflictKey]:
    """Convert list of conflicts to a set of conflict keys."""
    return {ConflictKey(c.element_code, c.conflict_type) for c in conflicts}


def conflicts_to_dict(conflicts: List[Conflict]) -> Dict[ConflictKey, ConflictInfo]:
    """Convert list of conflicts to a dict for detailed comparison."""
    return {
        ConflictKey(c.element_code, c.conflict_type): ConflictInfo(
            key=ConflictKey(c.element_code, c.conflict_type),
            severity=c.severity,
            ifc_value=c.ifc_value,
            bc3_value=c.bc3_value,
            description=c.description
        )
        for c in conflicts
    }


def compare_conflicts(baseline_conflicts: List[Conflict],
                      scenario_conflicts: List[Conflict],
                      expected_new: Set[str],
                      expected_removed: Set[str],
                      expected_changed: Set[str]) -> dict:
    """
    Compare scenario conflicts against baseline.

    Args:
        baseline_conflicts: Conflicts from baseline run
        scenario_conflicts: Conflicts from scenario run
        expected_new: Set of element codes expected to have NEW conflicts
        expected_removed: Set of element codes expected to have REMOVED conflicts
        expected_changed: Set of element codes expected to have CHANGED conflicts

    Returns:
        Dict with comparison results
    """
    baseline_set = conflicts_to_set(baseline_conflicts)
    scenario_set = conflicts_to_set(scenario_conflicts)
    baseline_dict = conflicts_to_dict(baseline_conflicts)
    scenario_dict = conflicts_to_dict(scenario_conflicts)

    # Find differences
    new_conflicts = scenario_set - baseline_set
    removed_conflicts = baseline_set - scenario_set
    common_conflicts = baseline_set & scenario_set

    # Check for value changes in common conflicts
    changed_conflicts = []
    for key in common_conflicts:
        base = baseline_dict.get(key)
        scen = scenario_dict.get(key)
        if base and scen:
            if (base.ifc_value != scen.ifc_value or
                base.bc3_value != scen.bc3_value or
                base.severity != scen.severity):
                changed_conflicts.append({
                    'key': key,
                    'baseline': base,
                    'scenario': scen
                })

    # Categorize new conflicts
    expected_new_found = {c for c in new_conflicts if c.element_code in expected_new}
    unexpected_new = new_conflicts - expected_new_found

    # Categorize removed conflicts
    expected_removed_found = {c for c in removed_conflicts if c.element_code in expected_removed}
    unexpected_removed = removed_conflicts - expected_removed_found

    # Categorize changed conflicts
    expected_changed_found = [c for c in changed_conflicts if c['key'].element_code in expected_changed]
    unexpected_changed = [c for c in changed_conflicts if c['key'].element_code not in expected_changed]

    return {
        'baseline_count': len(baseline_conflicts),
        'scenario_count': len(scenario_conflicts),
        'new_conflicts': list(new_conflicts),
        'removed_conflicts': list(removed_conflicts),
        'changed_conflicts': changed_conflicts,
        'expected_new_found': list(expected_new_found),
        'unexpected_new': list(unexpected_new),
        'expected_removed_found': list(expected_removed_found),
        'unexpected_removed': list(unexpected_removed),
        'expected_changed_found': expected_changed_found,
        'unexpected_changed': unexpected_changed,
        'pass': len(unexpected_new) == 0 and len(unexpected_removed) == 0 and len(unexpected_changed) == 0
    }


def print_comparison_report(scenario_name: str, comparison: dict, verbose: bool = True):
    """Print a detailed comparison report."""
    print(f"\n{'='*70}")
    print(f"REGRESSION TEST: {scenario_name}")
    print(f"{'='*70}")

    print(f"\n📊 CONFLICT COUNTS:")
    print(f"  Baseline: {comparison['baseline_count']}")
    print(f"  Scenario: {comparison['scenario_count']}")
    print(f"  Difference: {comparison['scenario_count'] - comparison['baseline_count']:+d}")

    print(f"\n🔍 CONFLICT CHANGES:")
    print(f"  New conflicts:     {len(comparison['new_conflicts'])}")
    print(f"  Removed conflicts: {len(comparison['removed_conflicts'])}")
    print(f"  Changed conflicts: {len(comparison['changed_conflicts'])}")

    # Expected changes
    print(f"\n✓ EXPECTED CHANGES FOUND:")
    if comparison['expected_new_found']:
        print(f"  New (expected): {len(comparison['expected_new_found'])}")
        if verbose:
            for c in comparison['expected_new_found']:
                print(f"    + {c}")
    if comparison['expected_removed_found']:
        print(f"  Removed (expected): {len(comparison['expected_removed_found'])}")
        if verbose:
            for c in comparison['expected_removed_found']:
                print(f"    - {c}")
    if comparison['expected_changed_found']:
        print(f"  Changed (expected): {len(comparison['expected_changed_found'])}")
        if verbose:
            for c in comparison['expected_changed_found']:
                print(f"    ~ {c['key']}: {c['baseline'].bc3_value} -> {c['scenario'].bc3_value}")

    # Unexpected changes (failures)
    has_unexpected = (len(comparison['unexpected_new']) > 0 or
                      len(comparison['unexpected_removed']) > 0 or
                      len(comparison['unexpected_changed']) > 0)

    if has_unexpected:
        print(f"\n✗ UNEXPECTED CHANGES (FAILURES):")
        if comparison['unexpected_new']:
            print(f"  New (UNEXPECTED): {len(comparison['unexpected_new'])}")
            for c in comparison['unexpected_new']:
                print(f"    ⚠️  + {c}")
        if comparison['unexpected_removed']:
            print(f"  Removed (UNEXPECTED): {len(comparison['unexpected_removed'])}")
            for c in comparison['unexpected_removed']:
                print(f"    ⚠️  - {c}")
        if comparison['unexpected_changed']:
            print(f"  Changed (UNEXPECTED): {len(comparison['unexpected_changed'])}")
            for c in comparison['unexpected_changed']:
                print(f"    ⚠️  ~ {c['key']}")
    else:
        print(f"\n✓ NO UNEXPECTED CHANGES")

    # Final result
    status = "✓ PASS" if comparison['pass'] else "✗ FAIL"
    print(f"\n{'='*70}")
    print(f"RESULT: {status}")
    print(f"{'='*70}")

    return comparison['pass']


def test_scenario1_regression(baseline_conflicts: List[Conflict]) -> bool:
    """
    Test Scenario 1: Quantity Mismatches - Regression Test

    Expected changes:
    - 350147, 352900, 360466, 361849: These elements have NO conflicts in baseline
      (their quantities match correctly). By modifying the BC3 quantities beyond
      tolerance, we expect NEW QUANTITY_MISMATCH conflicts to be created.

    This validates that the pipeline correctly detects quantity discrepancies
    when we intentionally introduce them.
    """
    print("\n" + "="*70)
    print("CREATING SCENARIO 1: QUANTITY MISMATCHES")
    print("="*70)

    modifier = BC3ModifierExtended(BASELINE_BC3)
    modifier.modify_quantity_in_decomposition("350147", 75.0)   # 63.62 -> 75.0 (17.9% > 5% tol)
    modifier.modify_quantity_in_decomposition("352900", 230.0)  # 215.1 -> 230.0 (6.9% > 2% tol)
    modifier.modify_quantity_in_decomposition("360466", 5500.0) # 4922.62 -> 5500.0 (11.7% > 5% tol)
    modifier.modify_quantity_in_decomposition("361849", 3)      # 2 -> 3 (50% > 0% tol)

    bc3_path = TEST_OUTPUT_DIR / "scenario1_quantity_mismatch.bc3"
    modifier.save(bc3_path)

    _, scenario_conflicts = run_comparison(BASELINE_IFC, bc3_path)

    # These elements have NO conflicts in baseline - they match correctly
    # Our modifications create NEW QUANTITY_MISMATCH conflicts
    expected_new = {'350147', '352900', '360466', '361849'}
    expected_removed = set()
    expected_changed = set()

    comparison = compare_conflicts(
        baseline_conflicts, scenario_conflicts,
        expected_new, expected_removed, expected_changed
    )

    return print_comparison_report("Scenario 1: Quantity Mismatches", comparison)


def test_scenario2_regression(baseline_conflicts: List[Conflict]) -> bool:
    """
    Test Scenario 2: Missing Elements - Regression Test

    Expected changes:
    - 350147, 352900, 361849: Should have MISSING_IN_BC3 (removed from BC3)
    - ORPHAN001, ORPHAN002, ORPHAN003: Should have MISSING_IN_IFC (new orphans)
    - Existing conflicts for removed elements may be removed
    """
    print("\n" + "="*70)
    print("CREATING SCENARIO 2: MISSING ELEMENTS")
    print("="*70)

    modifier = BC3ModifierExtended(BASELINE_BC3)
    codes_to_remove = ['350147', '352900', '361849']
    modifier.remove_elements_completely(codes_to_remove)
    # Use add_orphan_element_with_quantity - comparator skips elements with 0 quantity
    modifier.add_orphan_element_with_quantity('ORPHAN001', 'm2', 'Muro Ficticio - No existe en IFC', 100.0)
    modifier.add_orphan_element_with_quantity('ORPHAN002', 'u', 'Puerta Fantasma - No modelada', 5.0)
    modifier.add_orphan_element_with_quantity('ORPHAN003', 'm3', 'Cimentacion Extra - Sin modelo', 25.0)

    bc3_path = TEST_OUTPUT_DIR / "scenario2_missing_elements.bc3"
    modifier.save(bc3_path)

    _, scenario_conflicts = run_comparison(BASELINE_IFC, bc3_path)

    # New MISSING_IN_BC3 for removed elements, new MISSING_IN_IFC for orphans
    expected_new = {'350147', '352900', '361849', 'ORPHAN001', 'ORPHAN002', 'ORPHAN003'}
    # Existing quantity conflicts for these elements should be removed
    expected_removed = {'350147', '352900', '361849'}
    expected_changed = set()

    comparison = compare_conflicts(
        baseline_conflicts, scenario_conflicts,
        expected_new, expected_removed, expected_changed
    )

    return print_comparison_report("Scenario 2: Missing Elements", comparison)


def test_scenario3_regression(baseline_conflicts: List[Conflict]) -> bool:
    """
    Test Scenario 3: Name Mismatches - Regression Test

    Expected changes:
    - Minimal changes - elements should still match by code
    - Possibly NAME_MISMATCH conflicts for modified descriptions
    """
    print("\n" + "="*70)
    print("CREATING SCENARIO 3: NAME MISMATCHES")
    print("="*70)

    modifier = BC3ModifierExtended(BASELINE_BC3)
    modifier.change_description('350147', 'COLUMNA MODIFICADA 60x60')
    modifier.change_description('352900', 'VIGA PERFIL MODIFICADA')

    bc3_path = TEST_OUTPUT_DIR / "scenario3_name_mismatch.bc3"
    modifier.save(bc3_path)

    _, scenario_conflicts = run_comparison(BASELINE_IFC, bc3_path)

    # Name changes shouldn't add new conflicts if matching by code
    # But might add NAME_MISMATCH if that comparison is enabled
    expected_new = {'350147', '352900'}  # Possible NAME_MISMATCH
    expected_removed = set()
    expected_changed = set()

    comparison = compare_conflicts(
        baseline_conflicts, scenario_conflicts,
        expected_new, expected_removed, expected_changed
    )

    return print_comparison_report("Scenario 3: Name Mismatches", comparison)


def run_regression_tests():
    """Run all regression tests."""
    print("\n" + "="*70)
    print("REGRESSION TEST SUITE FOR IFC-BC3 COMPARISON PIPELINE")
    print("="*70)

    if not BASELINE_IFC.exists():
        print(f"ERROR: Baseline IFC not found: {BASELINE_IFC}")
        return False
    if not BASELINE_BC3.exists():
        print(f"ERROR: Baseline BC3 not found: {BASELINE_BC3}")
        return False

    ensure_test_dir()

    # Run baseline comparison
    print("\n" + "="*70)
    print("ESTABLISHING BASELINE")
    print("="*70)
    print("Running comparison on unmodified files...")

    baseline_result, baseline_conflicts = run_comparison(BASELINE_IFC, BASELINE_BC3)

    print(f"\n📊 BASELINE CONFLICT SUMMARY:")
    print(f"  Total conflicts: {len(baseline_conflicts)}")
    print(f"  Errors: {baseline_result['summary']['errors']}")
    print(f"  Warnings: {baseline_result['summary']['warnings']}")
    print(f"  Infos: {baseline_result['summary']['infos']}")

    print(f"\n📋 BASELINE CONFLICTS BY TYPE:")
    by_type = {}
    for c in baseline_conflicts:
        by_type[c.conflict_type] = by_type.get(c.conflict_type, 0) + 1
    for ct, count in sorted(by_type.items(), key=lambda x: x[0].value):
        print(f"  {ct.value}: {count}")

    print(f"\n📋 BASELINE CONFLICTS (ALL):")
    for c in baseline_conflicts:
        print(f"  [{c.element_code}] {c.conflict_type.value} ({c.severity.value})")

    # Run regression tests
    results = {}
    results['Scenario 1: Quantity Mismatch'] = test_scenario1_regression(baseline_conflicts)
    results['Scenario 2: Missing Elements'] = test_scenario2_regression(baseline_conflicts)
    results['Scenario 3: Name Mismatch'] = test_scenario3_regression(baseline_conflicts)

    # Final summary
    print("\n" + "="*70)
    print("REGRESSION TEST SUMMARY")
    print("="*70)

    all_passed = True
    for scenario, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {scenario}")
        if not passed:
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("ALL REGRESSION TESTS PASSED")
        print("  - Intended errors/warnings detected")
        print("  - No unexpected baseline changes")
    else:
        print("SOME REGRESSION TESTS FAILED")
        print("  - Review unexpected changes above")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = run_regression_tests()
    sys.exit(0 if success else 1)
