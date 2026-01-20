"""
Filters for excluding non-comparable elements from matching.

Some IFC/BC3 elements represent views, sheets, rooms, areas, etc.
that should not be compared as building elements. This module
provides filtering logic to exclude them.

Ported from Albert's implementation.
"""

from typing import Optional


# =============================================================================
# IGNORE TERMS
# =============================================================================
# Elements containing these terms in their description or code are filtered out.
# These represent non-comparable items like views, sheets, rooms, areas, etc.

IGNORE_TERMS_ES = [
    # Project info / views
    "información", "plano", "vista",
    # Zones and areas
    "zona de", "climatización", "topografía",
    # Rooms
    "habitaciones", "áreas", "ocupacion",
    "sup.libre", "sup.construida",
    # Room types
    "almacén", "salón", "cocina", "aseo", "archivo", "circulación",
    "área de trabajo", "sala de reuniones", "dep. limpieza",
    "aseos femeninos", "aseos masculinos",
    # Openings and voids
    "aberturas", "hueco", "corte", "líneas",
    # Materials and MEP
    "materiales", "tubería", "segmentos",
]

IGNORE_TERMS_EN = [
    # Project info / views
    "project info", "sheet", "view",
    # Zones and areas
    "rooms", "areas",
    # Openings and voids
    "opening", "void", "lines",
    # Materials and MEP
    "materials", "pipe",
    # Panels
    "system panel", "empty panel",
]

# Combined list
IGNORE_TERMS = IGNORE_TERMS_ES + IGNORE_TERMS_EN


def is_ignored_element(
    code: Optional[str],
    description: Optional[str],
    custom_terms: Optional[list[str]] = None
) -> bool:
    """
    Check if an element should be ignored (not compared).

    Elements are ignored if their code or description contains
    any of the ignore terms (case-insensitive).

    Args:
        code: Element code/identifier
        description: Element description/name
        custom_terms: Optional additional terms to check

    Returns:
        True if element should be ignored, False otherwise
    """
    # Build text to check (combine code and description)
    text_to_check = ""
    if code:
        text_to_check += str(code).lower() + " "
    if description:
        text_to_check += str(description).lower()

    if not text_to_check.strip():
        return False

    # Check against standard ignore terms
    terms = IGNORE_TERMS
    if custom_terms:
        terms = terms + custom_terms

    return any(term.lower() in text_to_check for term in terms)


def filter_elements(
    elements: dict,
    description_attr: str = "description",
    code_attr: str = "code",
    custom_terms: Optional[list[str]] = None
) -> dict:
    """
    Filter a dictionary of elements, removing ignored ones.

    Args:
        elements: Dictionary of elements {key: element}
        description_attr: Attribute name for description
        code_attr: Attribute name for code
        custom_terms: Optional additional terms to filter

    Returns:
        Filtered dictionary with ignored elements removed
    """
    result = {}
    for key, elem in elements.items():
        code = getattr(elem, code_attr, None) if hasattr(elem, code_attr) else key
        desc = getattr(elem, description_attr, None) if hasattr(elem, description_attr) else None

        if not is_ignored_element(code, desc, custom_terms):
            result[key] = elem

    return result


def get_ignored_elements(
    elements: dict,
    description_attr: str = "description",
    code_attr: str = "code",
    custom_terms: Optional[list[str]] = None
) -> dict:
    """
    Get only the ignored elements from a dictionary.

    Useful for reporting which elements were filtered out.

    Args:
        elements: Dictionary of elements {key: element}
        description_attr: Attribute name for description
        code_attr: Attribute name for code
        custom_terms: Optional additional terms to filter

    Returns:
        Dictionary containing only ignored elements
    """
    result = {}
    for key, elem in elements.items():
        code = getattr(elem, code_attr, None) if hasattr(elem, code_attr) else key
        desc = getattr(elem, description_attr, None) if hasattr(elem, description_attr) else None

        if is_ignored_element(code, desc, custom_terms):
            result[key] = elem

    return result
