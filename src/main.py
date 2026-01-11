"""
IFC-BC3 Conflict Flagger

Main entry point for comparing BIM models (IFC) with cost estimates (BC3).

Supports phase-based analysis:
- quick: Fast validation (codes, units, quantities only)
- full: Comprehensive comparison (all properties)
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter
from src.phases.config import Phase, get_phase_config


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare IFC model with BC3 budget and flag differences",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --ifc model.ifc --bc3 budget.bc3
  python -m src.main --ifc model.ifc --bc3 budget.bc3 --output report.xlsx
  python -m src.main --ifc model.ifc --bc3 budget.bc3 --json results.json
        """
    )

    parser.add_argument(
        "--ifc",
        required=True,
        help="Path to IFC file"
    )

    parser.add_argument(
        "--bc3",
        required=True,
        help="Path to BC3 file"
    )

    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output Excel report path (default: report_<timestamp>.xlsx)"
    )

    parser.add_argument(
        "--json",
        default=None,
        help="Output JSON report path (optional)"
    )

    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Numeric tolerance for value comparison (default: 0.01)"
    )

    parser.add_argument(
        "--no-name-matching",
        action="store_true",
        help="Disable fallback name-based matching"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode - only output file path"
    )

    parser.add_argument(
        "--phase",
        choices=["quick", "full"],
        default="full",
        help="Analysis phase: 'quick' (codes/quantities only) or 'full' (all properties). Default: full"
    )

    return parser.parse_args()


def print_summary(match_result, comparison_result, verbose=False):
    """Print a summary of results to console."""
    print("\n" + "=" * 60)
    print("IFC-BC3 COMPARISON RESULTS")
    print("=" * 60)

    print("\n📊 MATCHING SUMMARY")
    print(f"  Total IFC types:     {match_result.total_ifc_types}")
    print(f"  Total BC3 elements:  {match_result.total_bc3_elements}")
    print(f"  Matched:             {len(match_result.matched)}")
    print(f"  IFC only:            {len(match_result.ifc_only)} (not budgeted)")
    print(f"  BC3 only:            {len(match_result.bc3_only)} (orphan budget)")
    print(f"  Match rate:          {match_result.match_rate:.1f}%")

    print("\n🔍 CONFLICT SUMMARY")
    summary = comparison_result.summary()
    print(f"  Total conflicts:     {summary['total_conflicts']}")
    print(f"  🔴 Errors:           {summary['errors']}")
    print(f"  🟡 Warnings:         {summary['warnings']}")
    print(f"  Property mismatches: {summary['property_mismatches']}")

    if verbose and len(comparison_result.conflicts) > 0:
        print("\n📝 TOP CONFLICTS:")
        for conflict in comparison_result.conflicts[:10]:
            severity_icon = "🔴" if conflict.severity.value == "error" else "🟡"
            print(f"  {severity_icon} [{conflict.code}] {conflict.message}")

        if len(comparison_result.conflicts) > 10:
            print(f"  ... and {len(comparison_result.conflicts) - 10} more")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    args = parse_args()

    # Validate input files
    ifc_path = Path(args.ifc)
    bc3_path = Path(args.bc3)

    if not ifc_path.exists():
        print(f"Error: IFC file not found: {ifc_path}", file=sys.stderr)
        sys.exit(1)

    if not bc3_path.exists():
        print(f"Error: BC3 file not found: {bc3_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"report_{timestamp}.xlsx")

    # Get phase configuration
    phase = Phase.QUICK_CHECK if args.phase == "quick" else Phase.FULL_ANALYSIS
    phase_config = get_phase_config(phase)

    if not args.quiet:
        print(f"📂 IFC file: {ifc_path}")
        print(f"📂 BC3 file: {bc3_path}")
        print(f"📊 Output:   {output_path}")
        print(f"🔧 Phase:    {phase_config.name}")
        print("\nProcessing...")

    try:
        # Parse files
        if not args.quiet:
            print("  Parsing IFC file...")
        ifc_parser = IFCParser()
        ifc_result = ifc_parser.parse(ifc_path)

        if not args.quiet:
            print("  Parsing BC3 file...")
        bc3_parser = BC3Parser()
        bc3_result = bc3_parser.parse(bc3_path)

        # Match elements
        if not args.quiet:
            print("  Matching elements...")
        matcher = Matcher(match_by_name=not args.no_name_matching)
        match_result = matcher.match(ifc_result, bc3_result)

        # Compare matched elements (using phase configuration)
        if not args.quiet:
            print("  Comparing properties...")
        comparator = Comparator(tolerance=args.tolerance)
        comparison_result = comparator.compare(match_result, phase_config)

        # Generate report (using phase configuration)
        if not args.quiet:
            print("  Generating report...")
        reporter = Reporter()
        report_path = reporter.generate_report(
            match_result,
            comparison_result,
            output_path,
            phase_config=phase_config
        )

        # Generate JSON if requested
        if args.json:
            json_report = reporter.generate_json_report(match_result, comparison_result)
            json_path = Path(args.json)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_report, f, indent=2, ensure_ascii=False)
            if not args.quiet:
                print(f"  JSON report: {json_path}")

        # Print summary
        if not args.quiet:
            print_summary(match_result, comparison_result, args.verbose)
            print(f"\n✅ Report saved to: {report_path}")
        else:
            print(report_path)

        # Exit with error code if there are errors
        error_count = comparison_result.summary()['errors']
        if error_count > 0:
            sys.exit(2)  # Exit code 2 = errors found

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
