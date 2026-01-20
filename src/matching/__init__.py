"""
Matching module for linking IFC and BC3 elements.

Provides multiple matching strategies:
- TAG: Exact match by Tag/Code
- GUID: Match by IFC GlobalId
- NAME: Match by family/type name
- DESCRIPTION: Match by description similarity (Jaccard)
"""

from .matcher import (
    Matcher,
    MatchedPair,
    MatchResult,
    MatchStatus,
    MatchMethod,
)

from .filters import (
    is_ignored_element,
    filter_elements,
    get_ignored_elements,
    IGNORE_TERMS,
)

__all__ = [
    # Matcher
    "Matcher",
    "MatchedPair",
    "MatchResult",
    "MatchStatus",
    "MatchMethod",
    # Filters
    "is_ignored_element",
    "filter_elements",
    "get_ignored_elements",
    "IGNORE_TERMS",
]


