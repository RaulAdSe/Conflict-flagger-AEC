"""
Matching module for linking IFC and BC3 elements.

Provides multiple matching strategies:
- TAG: Exact match by Tag/Code
- GUID: Match by IFC GlobalId
- NAME: Match by family/type name
- DESCRIPTION: Match by description similarity (Jaccard)
"""

from src.matching.matcher import (
    Matcher,
    MatchMethod,
    MatchStatus,
    MatchedPair,
    MatchResult,
    normalize_description,
    calculate_similarity,
)

from src.matching.filters import (
    is_ignored_element,
    filter_elements,
    get_ignored_elements,
    IGNORE_TERMS,
)

__all__ = [
    # Matcher
    "Matcher",
    "MatchMethod",
    "MatchStatus",
    "MatchedPair",
    "MatchResult",
    # Similarity functions
    "normalize_description",
    "calculate_similarity",
    # Filters
    "is_ignored_element",
    "filter_elements",
    "get_ignored_elements",
    "IGNORE_TERMS",
]
