"""
Phase Configuration for Conflict Flagger AEC.

This module defines the different analysis phases available in the application.
Each phase represents a different level of analysis depth, from quick validation
to comprehensive property comparison.

DESIGN PRINCIPLES:
==================
1. MODULARITY: Phases are configurations, not separate code paths
2. REUSABILITY: All phases use the same parsers and core infrastructure
3. SCALABILITY: New phases can be added by simply defining a new PhaseConfig
4. FLEXIBILITY: Each phase controls what to check and what to report

HOW TO ADD A NEW PHASE:
=======================
1. Add a new enum value to Phase
2. Create a PhaseConfig with the desired settings
3. Add it to the PHASES dictionary
4. The UI will automatically show it as an option

Example:
    Phase.DETAILED_QUANTITIES: PhaseConfig(
        name="Detailed Quantities",
        description="Focus on quantity discrepancies with tight tolerance",
        check_quantities=True,
        quantity_tolerance=0.001,  # Very strict
        ...
    )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Phase(Enum):
    """
    Available analysis phases.

    Each phase represents a different depth of analysis, allowing users
    to choose between quick validation and comprehensive comparison.
    """
    QUICK_CHECK = "quick_check"      # Fast: codes, units, quantities only
    FULL_ANALYSIS = "full_analysis"  # Comprehensive: all properties


@dataclass
class PhaseConfig:
    """
    Configuration for an analysis phase.

    This dataclass defines what each phase checks and how it reports results.
    By modifying these settings, you control the behavior of the Comparator
    and Reporter without changing their code.

    Attributes:
        name: Human-readable name for UI display
        description: Explanation of what this phase does

        Comparison Settings:
        - check_codes: Verify that codes match between IFC and BC3
        - check_units: Compare measurement units (m, m2, m3, u, etc.)
        - check_quantities: Compare quantities with tolerance
        - check_properties: Deep comparison of all element properties
        - check_names: Compare family/type names
        - quantity_tolerance: Allowed difference for quantity comparison

        Reporting Settings:
        - sheets: Which Excel sheets to generate
        - include_summary: Whether to include the summary sheet
        - include_ok_matches: Show elements that match correctly
        - color_errors_only: Only highlight errors, not warnings
    """

    # Basic info
    name: str
    description: str = ""

    # What to compare
    check_codes: bool = True
    check_units: bool = True
    check_quantities: bool = True
    check_properties: bool = False  # Deep property comparison
    check_names: bool = False       # Family/type name comparison

    # Tolerances
    quantity_tolerance: float = 0.1

    # Reporting options
    sheets: list[str] = field(default_factory=list)
    include_summary: bool = True
    include_ok_matches: bool = True
    color_errors_only: bool = False

    def __post_init__(self):
        """Set default sheets if not provided."""
        if not self.sheets:
            self.sheets = ["Discrepancias"]


# =============================================================================
# PHASE DEFINITIONS
# =============================================================================
#
# These are the pre-configured phases available in the application.
# Albert's "quick check" concept is captured in QUICK_CHECK.
# The original comprehensive analysis is FULL_ANALYSIS.
#
# To add a new phase, simply add a new entry to this dictionary.
# =============================================================================

PHASES: dict[Phase, PhaseConfig] = {

    # -------------------------------------------------------------------------
    # PHASE 1: QUICK CHECK (Code & Quantity Matching)
    # -------------------------------------------------------------------------
    # Fast validation focusing on the most critical discrepancies:
    # - Code mismatches (elements matched by description with different codes)
    # - Quantity differences beyond tolerance
    # - Missing elements (in one file but not the other)
    #
    # Use case: Initial validation before detailed property analysis
    #
    # Output columns: Código BC3, Código IFC, Descripción, Unidad, Cant. BC3, Cant. IFC
    # -------------------------------------------------------------------------
    Phase.QUICK_CHECK: PhaseConfig(
        name="Fase 1: Códigos y Cantidades",
        description="Validación de códigos y cantidades. "
                    "Detecta emparejamientos por descripción (códigos diferentes) "
                    "y diferencias de cantidad. Ideal para revisión inicial.",

        # Only check the basics (no deep property comparison)
        check_codes=True,
        check_units=True,
        check_quantities=True,
        check_properties=False,  # Skip deep property comparison
        check_names=False,       # Skip name comparison

        # Tolerance for quantity comparison
        quantity_tolerance=0.1,

        # Phase 1 sheets: Discrepancies, Matches, Missing in Budget, Missing in Model
        sheets=[
            "Resumen",
            "Discrepancias",
            "Coincidencias",
            "Sin Presupuestar",
            "Sin Modelar",
        ],
        include_summary=True,
        include_ok_matches=True,  # Show matches in separate sheet
        color_errors_only=False,
    ),

    # -------------------------------------------------------------------------
    # PHASE 2: FULL ANALYSIS (Original comprehensive check)
    # -------------------------------------------------------------------------
    # Comprehensive comparison including:
    # - All checks from Quick Check
    # - Property-by-property comparison
    # - Family and type name verification
    # - Detailed reporting with all sheets
    #
    # Use case: Complete audit before project milestone
    # -------------------------------------------------------------------------
    Phase.FULL_ANALYSIS: PhaseConfig(
        name="Anàlisi Completa",
        description="Comparació exhaustiva de totes les propietats. "
                    "Inclou anàlisi detallada i informe complet amb totes les pestanyes.",

        # Check everything
        check_codes=True,
        check_units=True,
        check_quantities=True,
        check_properties=True,   # Deep property comparison
        check_names=True,        # Verify family/type names

        # Stricter tolerance for full analysis
        quantity_tolerance=0.01,

        # Complete reporting with all sheets
        sheets=[
            "Resumen",
            "Discrepancias",
            "Elementos Emparejados",
            "Sin Presupuestar",
            "Sin Modelar",
        ],
        include_summary=True,
        include_ok_matches=True,
        color_errors_only=False,
    ),
}


def get_phase_config(phase: Phase) -> PhaseConfig:
    """
    Get the configuration for a specific phase.

    Args:
        phase: The Phase enum value

    Returns:
        PhaseConfig for the requested phase

    Raises:
        KeyError: If the phase is not defined in PHASES
    """
    if phase not in PHASES:
        raise KeyError(f"Unknown phase: {phase}. Available phases: {list(PHASES.keys())}")
    return PHASES[phase]


def get_available_phases() -> list[tuple[Phase, str, str]]:
    """
    Get list of available phases for UI display.

    Returns:
        List of tuples: (Phase enum, display name, description)
    """
    return [
        (phase, config.name, config.description)
        for phase, config in PHASES.items()
    ]
