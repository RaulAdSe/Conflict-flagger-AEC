"""
Phase configuration for the comparison process.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class Phase(Enum):
    QUICK_CHECK = "quick"
    FULL_ANALYSIS = "full"


@dataclass
class PhaseConfig:
    """Configuration for a comparison phase."""
    name: str
    quantity_tolerance: float
    check_names: bool
    check_codes: bool
    include_warnings: bool
    include_summary: bool = True
    sheets: List[str] = field(default_factory=list)  # Excel sheets to generate
    

def get_phase_config(phase: Phase) -> PhaseConfig:
    """Get configuration for a specific phase."""
    configs = {
        Phase.QUICK_CHECK: PhaseConfig(
            name="Quick Check",
            quantity_tolerance=0.10,  # 10%
            check_names=False,
            check_codes=True,
            include_warnings=False,
            include_summary=True,
            sheets=["Resumen", "Discrepancias"]
        ),
        Phase.FULL_ANALYSIS: PhaseConfig(
            name="Full Analysis", 
            quantity_tolerance=0.05,  # 5%
            check_names=True,
            check_codes=True,
            include_warnings=True,
            include_summary=True,
            # Use names expected by reporter.py
            sheets=["Resumen", "Discrepancias", "Elementos Emparejados", "Sin Presupuestar", "Sin Modelar", "Resumen de Elementos"]
        )
    }
    return configs.get(phase, configs[Phase.FULL_ANALYSIS])