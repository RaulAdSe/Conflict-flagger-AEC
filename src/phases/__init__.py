"""
Phase configurations for the Conflict Flagger AEC application.

This module defines different analysis phases, from quick validation checks
to comprehensive property-by-property comparison. The phase-based architecture
allows the same core parsing and matching infrastructure to be reused across
different levels of analysis depth.

Architecture Philosophy:
- Phases are CONFIGURATIONS, not separate codebases
- All phases share the same parsers, matchers, and base infrastructure
- Each phase defines WHAT to check and HOW to report
- New phases can be added without modifying core logic

Available Phases:
- QUICK_CHECK: Fast validation of codes, units, and quantities
- FULL_ANALYSIS: Comprehensive comparison including all properties
"""

from .config import Phase, PhaseConfig, PHASES, get_phase_config

__all__ = ['Phase', 'PhaseConfig', 'PHASES', 'get_phase_config']
