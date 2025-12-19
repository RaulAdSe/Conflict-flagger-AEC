"""
Reporter for generating Excel reports with conflict visualization.

Generates color-coded Excel reports showing differences between IFC and BC3.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

from src.matching.matcher import MatchResult, MatchedPair, MatchStatus
from src.comparison.comparator import (
    ComparisonResult, Conflict, ConflictType, ConflictSeverity
)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    # Colors (RGB hex)
    color_error: str = "FF9999"  # Red
    color_warning: str = "FFFF99"  # Yellow
    color_ok: str = "99FF99"  # Green
    color_info: str = "99CCFF"  # Blue
    color_header: str = "4472C4"  # Dark blue

    # Display options
    show_ok_matches: bool = True
    show_info_conflicts: bool = False
    max_rows: int = 10000


class Reporter:
    """Generates Excel reports for IFC-BC3 comparison results."""

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize the reporter.

        Args:
            config: Report configuration options
        """
        self.config = config or ReportConfig()

    def generate_report(
        self,
        match_result: MatchResult,
        comparison_result: ComparisonResult,
        output_path: str | Path,
        include_summary: bool = True
    ) -> Path:
        """
        Generate an Excel report.

        Args:
            match_result: Result from the Matcher
            comparison_result: Result from the Comparator
            output_path: Path for the output Excel file
            include_summary: Whether to include a summary sheet

        Returns:
            Path to the generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        wb = Workbook()

        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

        # Create sheets
        if include_summary:
            self._create_summary_sheet(wb, match_result, comparison_result)

        self._create_conflicts_sheet(wb, comparison_result)
        self._create_matches_sheet(wb, match_result, comparison_result)
        self._create_missing_sheet(wb, match_result, "Missing in BC3", MatchStatus.IFC_ONLY)
        self._create_missing_sheet(wb, match_result, "Missing in IFC", MatchStatus.BC3_ONLY)

        wb.save(output_path)
        return output_path

    def _create_summary_sheet(
        self,
        wb: Workbook,
        match_result: MatchResult,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the summary sheet."""
        ws = wb.create_sheet("Summary", 0)

        # Title
        ws["A1"] = "IFC-BC3 Comparison Report"
        ws["A1"].font = Font(bold=True, size=16)
        ws.merge_cells("A1:D1")

        # Match statistics
        row = 3
        ws[f"A{row}"] = "Matching Statistics"
        ws[f"A{row}"].font = Font(bold=True, size=12)

        stats = [
            ("Total IFC Types", match_result.total_ifc_types),
            ("Total BC3 Elements", match_result.total_bc3_elements),
            ("Matched", len(match_result.matched)),
            ("IFC Only (Not Budgeted)", len(match_result.ifc_only)),
            ("BC3 Only (Orphan Budget)", len(match_result.bc3_only)),
            ("Match Rate", f"{match_result.match_rate:.1f}%"),
        ]

        row += 1
        for label, value in stats:
            ws[f"A{row}"] = label
            ws[f"B{row}"] = value
            row += 1

        # Comparison statistics
        row += 1
        ws[f"A{row}"] = "Comparison Results"
        ws[f"A{row}"].font = Font(bold=True, size=12)

        summary = comparison_result.summary()
        comp_stats = [
            ("Total Conflicts", summary["total_conflicts"]),
            ("Errors (Value Mismatches)", summary["errors"]),
            ("Warnings (Missing Elements)", summary["warnings"]),
            ("Property Mismatches", summary["property_mismatches"]),
        ]

        row += 1
        for label, value in comp_stats:
            ws[f"A{row}"] = label
            ws[f"B{row}"] = value

            # Color code
            if "Error" in label and value > 0:
                ws[f"B{row}"].fill = PatternFill(
                    start_color=self.config.color_error,
                    end_color=self.config.color_error,
                    fill_type="solid"
                )
            elif "Warning" in label and value > 0:
                ws[f"B{row}"].fill = PatternFill(
                    start_color=self.config.color_warning,
                    end_color=self.config.color_warning,
                    fill_type="solid"
                )

            row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 15

    def _create_conflicts_sheet(
        self,
        wb: Workbook,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the conflicts detail sheet."""
        ws = wb.create_sheet("Conflicts")

        # Headers
        headers = ["Code", "Element", "Type", "Severity", "Property", "IFC Value", "BC3 Value", "Message"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color=self.config.color_header,
                end_color=self.config.color_header,
                fill_type="solid"
            )
            cell.alignment = Alignment(horizontal="center")

        # Filter conflicts
        conflicts = comparison_result.conflicts
        if not self.config.show_info_conflicts:
            conflicts = [c for c in conflicts if c.severity != ConflictSeverity.INFO]

        # Add conflict rows
        for row_num, conflict in enumerate(conflicts[:self.config.max_rows], 2):
            ws.cell(row=row_num, column=1, value=conflict.code or "")
            ws.cell(row=row_num, column=2, value=conflict.element_name)
            ws.cell(row=row_num, column=3, value=conflict.conflict_type.value)
            ws.cell(row=row_num, column=4, value=conflict.severity.value.upper())
            ws.cell(row=row_num, column=5, value=conflict.property_name or "")
            ws.cell(row=row_num, column=6, value=str(conflict.ifc_value) if conflict.ifc_value is not None else "")
            ws.cell(row=row_num, column=7, value=str(conflict.bc3_value) if conflict.bc3_value is not None else "")
            ws.cell(row=row_num, column=8, value=conflict.message)

            # Color by severity
            fill_color = self._get_severity_color(conflict.severity)
            for col in range(1, 9):
                ws.cell(row=row_num, column=col).fill = PatternFill(
                    start_color=fill_color,
                    end_color=fill_color,
                    fill_type="solid"
                )

        self._auto_width_columns(ws)

    def _create_matches_sheet(
        self,
        wb: Workbook,
        match_result: MatchResult,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the matched elements sheet."""
        ws = wb.create_sheet("Matched Elements")

        # Headers
        headers = ["Code", "IFC Name", "BC3 Description", "Match Method", "Status", "Conflicts"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color=self.config.color_header,
                end_color=self.config.color_header,
                fill_type="solid"
            )

        # Build conflict count map
        conflict_counts = {}
        for conflict in comparison_result.conflicts:
            if conflict.code:
                conflict_counts[conflict.code] = conflict_counts.get(conflict.code, 0) + 1

        # Add matched rows
        for row_num, pair in enumerate(match_result.matched[:self.config.max_rows], 2):
            code = pair.code or ""
            ifc_name = pair.ifc_type.name if pair.ifc_type else ""
            bc3_desc = pair.bc3_element.description if pair.bc3_element else ""
            method = pair.method.value
            num_conflicts = conflict_counts.get(code, 0)

            status = "OK" if num_conflicts == 0 else f"{num_conflicts} conflicts"

            ws.cell(row=row_num, column=1, value=code)
            ws.cell(row=row_num, column=2, value=ifc_name)
            ws.cell(row=row_num, column=3, value=bc3_desc)
            ws.cell(row=row_num, column=4, value=method)
            ws.cell(row=row_num, column=5, value=status)
            ws.cell(row=row_num, column=6, value=num_conflicts)

            # Color by status
            if num_conflicts == 0:
                fill_color = self.config.color_ok
            else:
                fill_color = self.config.color_error

            for col in range(1, 7):
                ws.cell(row=row_num, column=col).fill = PatternFill(
                    start_color=fill_color,
                    end_color=fill_color,
                    fill_type="solid"
                )

        self._auto_width_columns(ws)

    def _create_missing_sheet(
        self,
        wb: Workbook,
        match_result: MatchResult,
        sheet_name: str,
        status: MatchStatus
    ) -> None:
        """Create a sheet for missing elements."""
        ws = wb.create_sheet(sheet_name)

        if status == MatchStatus.IFC_ONLY:
            items = match_result.ifc_only
            headers = ["Code/Tag", "Name", "IFC Class", "Family", "Type"]
        else:
            items = match_result.bc3_only
            headers = ["Code", "Description", "Unit", "Price", "Family", "Type"]

        # Headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color=self.config.color_header,
                end_color=self.config.color_header,
                fill_type="solid"
            )

        # Add rows
        for row_num, pair in enumerate(items[:self.config.max_rows], 2):
            if status == MatchStatus.IFC_ONLY and pair.ifc_type:
                ifc = pair.ifc_type
                ws.cell(row=row_num, column=1, value=ifc.tag or ifc.global_id)
                ws.cell(row=row_num, column=2, value=ifc.name)
                ws.cell(row=row_num, column=3, value=ifc.ifc_class)
                ws.cell(row=row_num, column=4, value=ifc.family_name or "")
                ws.cell(row=row_num, column=5, value=ifc.type_name or "")
            elif status == MatchStatus.BC3_ONLY and pair.bc3_element:
                bc3 = pair.bc3_element
                ws.cell(row=row_num, column=1, value=bc3.code)
                ws.cell(row=row_num, column=2, value=bc3.description)
                ws.cell(row=row_num, column=3, value=bc3.unit)
                ws.cell(row=row_num, column=4, value=bc3.price)
                ws.cell(row=row_num, column=5, value=bc3.family_name or "")
                ws.cell(row=row_num, column=6, value=bc3.type_name or "")

            # Yellow warning color
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=col).fill = PatternFill(
                    start_color=self.config.color_warning,
                    end_color=self.config.color_warning,
                    fill_type="solid"
                )

        self._auto_width_columns(ws)

    def _get_severity_color(self, severity: ConflictSeverity) -> str:
        """Get the color for a severity level."""
        if severity == ConflictSeverity.ERROR:
            return self.config.color_error
        elif severity == ConflictSeverity.WARNING:
            return self.config.color_warning
        elif severity == ConflictSeverity.INFO:
            return self.config.color_info
        return "FFFFFF"

    def _auto_width_columns(self, ws) -> None:
        """Auto-adjust column widths based on content."""
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    def generate_json_report(
        self,
        match_result: MatchResult,
        comparison_result: ComparisonResult
    ) -> dict:
        """
        Generate a JSON-serializable report.

        Args:
            match_result: Result from the Matcher
            comparison_result: Result from the Comparator

        Returns:
            Dictionary with report data
        """
        return {
            "summary": {
                "matching": match_result.summary(),
                "comparison": comparison_result.summary()
            },
            "conflicts": [
                {
                    "code": c.code,
                    "element": c.element_name,
                    "type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "property": c.property_name,
                    "ifc_value": str(c.ifc_value) if c.ifc_value is not None else None,
                    "bc3_value": str(c.bc3_value) if c.bc3_value is not None else None,
                    "message": c.message
                }
                for c in comparison_result.conflicts
            ],
            "matched": [
                {
                    "code": p.code,
                    "method": p.method.value,
                    "confidence": p.confidence
                }
                for p in match_result.matched
            ],
            "ifc_only": [
                {"code": p.code, "name": p.name}
                for p in match_result.ifc_only
            ],
            "bc3_only": [
                {"code": p.code, "name": p.name}
                for p in match_result.bc3_only
            ]
        }
