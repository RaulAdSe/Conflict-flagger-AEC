"""
Reporter for generating Excel reports with conflict visualization.

Generates color-coded Excel reports showing differences between IFC and BC3.
Reports are in Spanish for AEC professionals.

PHASE SUPPORT:
==============
The generate_report() method accepts an optional PhaseConfig that controls:
- Which sheets to generate
- Whether to include summary sheet
- Whether to show OK matches

This allows the same Reporter to produce different outputs for quick checks
vs comprehensive analysis without code duplication.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.matching.matcher import MatchResult, MatchedPair, MatchStatus
from src.comparison.comparator import (
    ComparisonResult, Conflict, ConflictType, ConflictSeverity
)

# Import PhaseConfig only for type checking to avoid circular imports
if TYPE_CHECKING:
    from src.phases.config import PhaseConfig


# Spanish translations for conflict types and messages
TRANSLATIONS = {
    # Conflict types
    "property_mismatch": "Diferencia de valor",
    "missing_in_bc3": "Falta en presupuesto",
    "missing_in_ifc": "Falta en modelo",
    "quantity_mismatch": "Diferencia de cantidad",
    "type_mismatch": "Diferencia de tipo",

    # Severity levels
    "error": "ERROR",
    "warning": "AVISO",
    "info": "INFO",

    # Match methods
    "guid": "Por GUID",
    "tag": "Por Tag/ID",
    "name": "Por nombre",
    "type_name": "Por tipo",

    # Common messages
    "Element exists in IFC but not in BC3 budget": "Elemento existe en el modelo IFC pero no en el presupuesto BC3",
    "Element exists in BC3 but not in IFC model": "Elemento existe en el presupuesto BC3 pero no en el modelo IFC",
}


def translate(text: str) -> str:
    """Translate text to Spanish if translation exists."""
    return TRANSLATIONS.get(text, text)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    # Colors (RGB hex)
    color_error: str = "FF6B6B"  # Soft red
    color_warning: str = "FFE66D"  # Soft yellow
    color_ok: str = "7ED957"  # Soft green
    color_info: str = "74C0FC"  # Soft blue
    color_header: str = "2E86AB"  # Professional blue

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
        self._thin_border = Border(
            left=Side(style='thin', color='CCCCCC'),
            right=Side(style='thin', color='CCCCCC'),
            top=Side(style='thin', color='CCCCCC'),
            bottom=Side(style='thin', color='CCCCCC')
        )

    def generate_report(
        self,
        match_result: MatchResult,
        comparison_result: ComparisonResult,
        output_path: str | Path,
        include_summary: bool = True,
        phase_config: 'PhaseConfig' = None
    ) -> Path:
        """
        Generate an Excel report.

        Args:
            match_result: Result from the Matcher
            comparison_result: Result from the Comparator
            output_path: Path for the output Excel file
            include_summary: Whether to include a summary sheet (can be overridden by phase_config)
            phase_config: Optional phase configuration that controls which sheets to generate.
                         If None, generates all sheets (full analysis mode).

        Returns:
            Path to the generated report

        Phase Support:
            - QUICK_CHECK: Generates only Discrepàncies sheet
            - FULL_ANALYSIS: Generates all sheets (Resumen, Discrepancias, etc.)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        wb = Workbook()

        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

        # Determine which sheets to generate based on phase config
        if phase_config is not None:
            sheets_to_generate = set(phase_config.sheets)
            include_summary = phase_config.include_summary
        else:
            # Default to all sheets (full analysis)
            sheets_to_generate = {"Resumen", "Discrepancias", "Elementos Emparejados",
                                  "Sin Presupuestar", "Sin Modelar"}

        # Create sheets based on configuration
        if include_summary and ("Resumen" in sheets_to_generate or "Resum" in sheets_to_generate):
            self._create_summary_sheet(wb, match_result, comparison_result)

        # Discrepancies sheet (always included in any phase)
        if any(s in sheets_to_generate for s in ["Discrepancias", "Discrepàncies"]):
            self._create_conflicts_sheet(wb, comparison_result)

        # Matched elements sheet
        if "Elementos Emparejados" in sheets_to_generate:
            self._create_matches_sheet(wb, match_result, comparison_result)

        # Missing in budget sheet
        if "Sin Presupuestar" in sheets_to_generate:
            self._create_missing_sheet(wb, match_result, "Sin Presupuestar", MatchStatus.IFC_ONLY)

        # Missing in model sheet
        if "Sin Modelar" in sheets_to_generate:
            self._create_missing_sheet(wb, match_result, "Sin Modelar", MatchStatus.BC3_ONLY)

        wb.save(output_path)
        return output_path

    def _apply_header_style(self, cell) -> None:
        """Apply header styling to a cell."""
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(
            start_color=self.config.color_header,
            end_color=self.config.color_header,
            fill_type="solid"
        )
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = self._thin_border

    def _apply_cell_style(self, cell, fill_color: str = None) -> None:
        """Apply standard cell styling."""
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = self._thin_border
        if fill_color:
            cell.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid"
            )

    def _create_summary_sheet(
        self,
        wb: Workbook,
        match_result: MatchResult,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the summary sheet."""
        ws = wb.create_sheet("Resumen", 0)

        # Title
        ws["A1"] = "INFORME DE COMPARACION IFC - BC3"
        ws["A1"].font = Font(bold=True, size=18, color="2E86AB")
        ws.merge_cells("A1:D1")
        ws.row_dimensions[1].height = 30

        # Subtitle with date
        ws["A2"] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws["A2"].font = Font(italic=True, size=10, color="666666")
        ws.merge_cells("A2:D2")

        # Summary box
        row = 4
        ws[f"A{row}"] = "RESUMEN EJECUTIVO"
        ws[f"A{row}"].font = Font(bold=True, size=14)
        ws.merge_cells(f"A{row}:D{row}")

        row += 1
        summary = comparison_result.summary()
        total_issues = summary["errors"] + summary["warnings"]

        if total_issues == 0:
            status_text = "Sin discrepancias detectadas"
            status_color = self.config.color_ok
        elif summary["errors"] > 0:
            status_text = f"{summary['errors']} errores y {summary['warnings']} avisos detectados"
            status_color = self.config.color_error
        else:
            status_text = f"{summary['warnings']} avisos detectados"
            status_color = self.config.color_warning

        ws[f"A{row}"] = status_text
        ws[f"A{row}"].font = Font(bold=True, size=12)
        ws[f"A{row}"].fill = PatternFill(start_color=status_color, end_color=status_color, fill_type="solid")
        ws.merge_cells(f"A{row}:D{row}")

        # Match statistics section
        row += 2
        ws[f"A{row}"] = "ESTADISTICAS DE EMPAREJAMIENTO"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        ws.merge_cells(f"A{row}:D{row}")

        stats = [
            ("Tipos en modelo IFC", match_result.total_ifc_types, "Familias/tipos encontrados en el archivo IFC"),
            ("Partidas en presupuesto BC3", match_result.total_bc3_elements, "Elementos encontrados en el archivo BC3"),
            ("Emparejados correctamente", len(match_result.matched), "Elementos que coinciden entre modelo y presupuesto"),
            ("Solo en IFC (sin presupuestar)", len(match_result.ifc_only), "Elementos modelados pero no incluidos en presupuesto"),
            ("Solo en BC3 (sin modelar)", len(match_result.bc3_only), "Partidas presupuestadas pero no modeladas"),
            ("Tasa de emparejamiento", f"{match_result.match_rate:.1f}%", "Porcentaje de elementos emparejados"),
        ]

        row += 1
        headers = ["Concepto", "Valor", "Descripcion"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)

        row += 1
        for label, value, description in stats:
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=2, value=value)
            ws.cell(row=row, column=3, value=description)
            for col in range(1, 4):
                self._apply_cell_style(ws.cell(row=row, column=col))
            row += 1

        # Comparison results section
        row += 1
        ws[f"A{row}"] = "RESULTADOS DE LA COMPARACION"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        ws.merge_cells(f"A{row}:D{row}")

        comp_stats = [
            ("Total de discrepancias", summary["total_conflicts"], self.config.color_info, "Numero total de diferencias encontradas"),
            ("Errores (diferencias de valor)", summary["errors"], self.config.color_error if summary["errors"] > 0 else None, "Valores que no coinciden entre modelo y presupuesto"),
            ("Avisos (elementos faltantes)", summary["warnings"], self.config.color_warning if summary["warnings"] > 0 else None, "Elementos que existen en uno pero no en otro"),
            ("Discrepancias en propiedades", summary["property_mismatches"], None, "Propiedades con valores diferentes"),
        ]

        row += 1
        headers = ["Tipo", "Cantidad", "Descripcion"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)

        row += 1
        for label, value, color, description in comp_stats:
            ws.cell(row=row, column=1, value=label)
            cell_value = ws.cell(row=row, column=2, value=value)
            ws.cell(row=row, column=3, value=description)
            for col in range(1, 4):
                self._apply_cell_style(ws.cell(row=row, column=col), color if col == 2 else None)
            row += 1

        # Legend
        row += 2
        ws[f"A{row}"] = "LEYENDA DE COLORES"
        ws[f"A{row}"].font = Font(bold=True, size=11)

        row += 1
        legend = [
            (self.config.color_error, "Rojo", "Error - Requiere atencion inmediata"),
            (self.config.color_warning, "Amarillo", "Aviso - Revisar"),
            (self.config.color_ok, "Verde", "Correcto - Sin problemas"),
        ]

        for color, name, desc in legend:
            ws.cell(row=row, column=1, value="")
            ws.cell(row=row, column=1).fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            ws.cell(row=row, column=2, value=name)
            ws.cell(row=row, column=3, value=desc)
            row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 50
        ws.column_dimensions["D"].width = 15

    def _create_conflicts_sheet(
        self,
        wb: Workbook,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the conflicts detail sheet."""
        ws = wb.create_sheet("Discrepancias")

        # Headers in Spanish
        headers = [
            ("Codigo", 15),
            ("Elemento", 30),
            ("Tipo de Discrepancia", 25),
            ("Gravedad", 12),
            ("Propiedad", 20),
            ("Valor IFC (Modelo)", 20),
            ("Valor BC3 (Presupuesto)", 20),
            ("Descripcion del Problema", 50)
        ]

        for col, (header, width) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._apply_header_style(cell)
            ws.column_dimensions[get_column_letter(col)].width = width

        ws.row_dimensions[1].height = 25

        # Filter conflicts
        conflicts = comparison_result.conflicts
        if not self.config.show_info_conflicts:
            conflicts = [c for c in conflicts if c.severity != ConflictSeverity.INFO]

        # Add conflict rows
        for row_num, conflict in enumerate(conflicts[:self.config.max_rows], 2):
            # Translate values
            conflict_type_es = translate(conflict.conflict_type.value)
            severity_es = translate(conflict.severity.value)
            message_es = translate(conflict.message)

            ws.cell(row=row_num, column=1, value=conflict.code or "")
            ws.cell(row=row_num, column=2, value=conflict.element_name)
            ws.cell(row=row_num, column=3, value=conflict_type_es)
            ws.cell(row=row_num, column=4, value=severity_es)
            ws.cell(row=row_num, column=5, value=conflict.property_name or "-")
            ws.cell(row=row_num, column=6, value=str(conflict.ifc_value) if conflict.ifc_value is not None else "-")
            ws.cell(row=row_num, column=7, value=str(conflict.bc3_value) if conflict.bc3_value is not None else "-")
            ws.cell(row=row_num, column=8, value=message_es)

            # Color by severity
            fill_color = self._get_severity_color(conflict.severity)
            for col in range(1, 9):
                self._apply_cell_style(ws.cell(row=row_num, column=col), fill_color)

        # Freeze header row
        ws.freeze_panes = "A2"

    def _create_matches_sheet(
        self,
        wb: Workbook,
        match_result: MatchResult,
        comparison_result: ComparisonResult
    ) -> None:
        """Create the matched elements sheet."""
        ws = wb.create_sheet("Elementos Emparejados")

        # Headers in Spanish
        headers = [
            ("Codigo/Tag", 15),
            ("Nombre en IFC", 35),
            ("Descripcion en BC3", 40),
            ("Metodo de Emparejamiento", 25),
            ("Estado", 20),
            ("Num. Discrepancias", 18)
        ]

        for col, (header, width) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._apply_header_style(cell)
            ws.column_dimensions[get_column_letter(col)].width = width

        ws.row_dimensions[1].height = 25

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
            method = translate(pair.method.value)
            num_conflicts = conflict_counts.get(code, 0)

            if num_conflicts == 0:
                status = "Correcto"
                fill_color = self.config.color_ok
            else:
                status = f"{num_conflicts} discrepancia(s)"
                fill_color = self.config.color_error

            ws.cell(row=row_num, column=1, value=code)
            ws.cell(row=row_num, column=2, value=ifc_name)
            ws.cell(row=row_num, column=3, value=bc3_desc)
            ws.cell(row=row_num, column=4, value=method)
            ws.cell(row=row_num, column=5, value=status)
            ws.cell(row=row_num, column=6, value=num_conflicts)

            for col in range(1, 7):
                self._apply_cell_style(ws.cell(row=row_num, column=col), fill_color)

        # Freeze header row
        ws.freeze_panes = "A2"

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
            headers = [
                ("Codigo/Tag", 15),
                ("Nombre", 35),
                ("Clase IFC", 20),
                ("Familia", 25),
                ("Tipo", 25),
                ("Accion Requerida", 40)
            ]
            action_text = "Incluir en presupuesto BC3"
        else:
            items = match_result.bc3_only
            headers = [
                ("Codigo", 15),
                ("Descripcion", 40),
                ("Unidad", 10),
                ("Precio", 15),
                ("Familia", 25),
                ("Accion Requerida", 40)
            ]
            action_text = "Modelar en IFC o eliminar del presupuesto"

        # Headers
        for col, (header, width) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._apply_header_style(cell)
            ws.column_dimensions[get_column_letter(col)].width = width

        ws.row_dimensions[1].height = 25

        # Add rows
        for row_num, pair in enumerate(items[:self.config.max_rows], 2):
            if status == MatchStatus.IFC_ONLY and pair.ifc_type:
                ifc = pair.ifc_type
                ws.cell(row=row_num, column=1, value=ifc.tag or ifc.global_id)
                ws.cell(row=row_num, column=2, value=ifc.name)
                ws.cell(row=row_num, column=3, value=ifc.ifc_class)
                ws.cell(row=row_num, column=4, value=ifc.family_name or "-")
                ws.cell(row=row_num, column=5, value=ifc.type_name or "-")
                ws.cell(row=row_num, column=6, value=action_text)
            elif status == MatchStatus.BC3_ONLY and pair.bc3_element:
                bc3 = pair.bc3_element
                ws.cell(row=row_num, column=1, value=bc3.code)
                ws.cell(row=row_num, column=2, value=bc3.description)
                ws.cell(row=row_num, column=3, value=bc3.unit)
                ws.cell(row=row_num, column=4, value=f"{bc3.price:.2f} EUR" if bc3.price else "-")
                ws.cell(row=row_num, column=5, value=bc3.family_name or "-")
                ws.cell(row=row_num, column=6, value=action_text)

            # Warning color for all missing items
            for col in range(1, len(headers) + 1):
                self._apply_cell_style(ws.cell(row=row_num, column=col), self.config.color_warning)

        # Freeze header row
        ws.freeze_panes = "A2"

    def _get_severity_color(self, severity: ConflictSeverity) -> str:
        """Get the color for a severity level."""
        if severity == ConflictSeverity.ERROR:
            return self.config.color_error
        elif severity == ConflictSeverity.WARNING:
            return self.config.color_warning
        elif severity == ConflictSeverity.INFO:
            return self.config.color_info
        return "FFFFFF"

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
            "resumen": {
                "fecha_generacion": datetime.now().isoformat(),
                "emparejamiento": {
                    "total_tipos_ifc": match_result.total_ifc_types,
                    "total_elementos_bc3": match_result.total_bc3_elements,
                    "emparejados": len(match_result.matched),
                    "solo_ifc": len(match_result.ifc_only),
                    "solo_bc3": len(match_result.bc3_only),
                    "tasa_emparejamiento": f"{match_result.match_rate:.1f}%"
                },
                "comparacion": comparison_result.summary()
            },
            "discrepancias": [
                {
                    "codigo": c.code,
                    "elemento": c.element_name,
                    "tipo": translate(c.conflict_type.value),
                    "gravedad": translate(c.severity.value),
                    "propiedad": c.property_name,
                    "valor_ifc": str(c.ifc_value) if c.ifc_value is not None else None,
                    "valor_bc3": str(c.bc3_value) if c.bc3_value is not None else None,
                    "mensaje": translate(c.message)
                }
                for c in comparison_result.conflicts
            ],
            "emparejados": [
                {
                    "codigo": p.code,
                    "metodo": translate(p.method.value),
                    "confianza": p.confidence
                }
                for p in match_result.matched
            ],
            "solo_ifc": [
                {"codigo": p.code, "nombre": p.name}
                for p in match_result.ifc_only
            ],
            "solo_bc3": [
                {"codigo": p.code, "nombre": p.name}
                for p in match_result.bc3_only
            ]
        }
