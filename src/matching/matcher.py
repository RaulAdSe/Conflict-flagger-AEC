"""
Matcher module - Matches IFC types with BC3 elements.

Supports matching by:
1. Tag/Code (exact match)
2. Type IFC GUID
3. Name/Description similarity
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import re


class MatchMethod(Enum):
    """Method used to match IFC type with BC3 element."""
    BY_TAG = "Por Tag/ID"
    BY_GUID = "Por GUID"
    BY_NAME = "Por Nombre/Descripción"


class MatchStatus(str, Enum):
    """Status of a matched element."""
    MATCHED = "matched"
    IFC_ONLY = "ifc_only"
    BC3_ONLY = "bc3_only"


@dataclass
class MatchedPair:
    """A matched pair of IFC type and BC3 element."""
    ifc_type: any  # IFCType
    bc3_element: any  # BC3Element
    match_method: str  # 'Por Tag/ID', 'Por GUID', 'Por Nombre/Descripción'
    match_score: float = 1.0  # 0-1, higher is better


@dataclass
class MatchResult:
    """Result of the matching process."""
    matched: list  # List of MatchedPair
    ifc_only: list  # IFC types without BC3 match
    bc3_only: list  # BC3 elements without IFC match
    total_ifc_types: int = 0  # Total IFC types processed
    total_bc3_elements: int = 0  # Total BC3 elements processed
    
    @property
    def match_rate(self) -> float:
        """Calculate match rate as percentage."""
        total = self.total_ifc_types + self.total_bc3_elements
        if total == 0:
            return 0.0
        matched_count = len(self.matched) * 2  # Each match covers 1 IFC + 1 BC3
        return (matched_count / total) * 100


class Matcher:
    """Matches IFC types with BC3 elements."""
    
    def __init__(self, match_by_name: bool = True, name_threshold: float = 0.5):
        self.match_by_name = match_by_name
        self.name_threshold = name_threshold
    
    def match(self, ifc_result, bc3_result) -> MatchResult:
        """
        Match IFC types with BC3 elements.
        
        Priority:
        1. Exact Tag match (IFC Type Tag == BC3 Code)
        2. Type IFC GUID match
        3. Name similarity match (if enabled)
        """
        matched = []
        ifc_only = []
        bc3_only = []
        
        # Track what's been matched
        matched_ifc_ids = set()
        matched_bc3_codes = set()
        
        ifc_types = list(ifc_result.types.values())
        # Filter BC3 elements: only include elements with a unit (not chapters/groupers)
        # Elements without unit are typically grouping chapters, not real types
        bc3_elements = [e for e in bc3_result.elements.values() if e.unit]
        
        # Phase 1: Match by Tag/Code
        for ifc_type in ifc_types:
            if ifc_type.tag and ifc_type.tag in bc3_result.elements:
                bc3_elem = bc3_result.elements[ifc_type.tag]
                matched.append(MatchedPair(
                    ifc_type=ifc_type,
                    bc3_element=bc3_elem,
                    match_method=MatchMethod.BY_TAG,
                    match_score=1.0
                ))
                matched_ifc_ids.add(ifc_type.global_id)
                matched_bc3_codes.add(bc3_elem.code)
        
        # Phase 2: Match by Type IFC GUID
        for bc3_elem in bc3_elements:
            if bc3_elem.code in matched_bc3_codes:
                continue
            
            if bc3_elem.type_ifc_guid:
                # Find IFC type with this GUID
                for ifc_type in ifc_types:
                    if ifc_type.global_id in matched_ifc_ids:
                        continue
                    if ifc_type.global_id == bc3_elem.type_ifc_guid:
                        matched.append(MatchedPair(
                            ifc_type=ifc_type,
                            bc3_element=bc3_elem,
                            match_method=MatchMethod.BY_GUID,
                            match_score=1.0
                        ))
                        matched_ifc_ids.add(ifc_type.global_id)
                        matched_bc3_codes.add(bc3_elem.code)
                        break
        
        # Phase 3: Match by Name (if enabled)
        if self.match_by_name:
            unmatched_ifc = [t for t in ifc_types if t.global_id not in matched_ifc_ids]
            unmatched_bc3 = [e for e in bc3_elements if e.code not in matched_bc3_codes]
            
            for bc3_elem in unmatched_bc3:
                best_match = None
                best_score = self.name_threshold
                
                bc3_name = self._normalize_name(bc3_elem.description)
                
                for ifc_type in unmatched_ifc:
                    if ifc_type.global_id in matched_ifc_ids:
                        continue
                    
                    ifc_name = self._normalize_name(ifc_type.name)
                    score = self._calc_similarity(bc3_name, ifc_name)
                    
                    if score > best_score:
                        best_score = score
                        best_match = ifc_type
                
                if best_match:
                    matched.append(MatchedPair(
                        ifc_type=best_match,
                        bc3_element=bc3_elem,
                        match_method=MatchMethod.BY_NAME,
                        match_score=best_score
                    ))
                    matched_ifc_ids.add(best_match.global_id)
                    matched_bc3_codes.add(bc3_elem.code)
        
        # Collect unmatched
        ifc_only = [t for t in ifc_types if t.global_id not in matched_ifc_ids]
        bc3_only = [e for e in bc3_elements if e.code not in matched_bc3_codes]
        
        return MatchResult(
            matched=matched,
            ifc_only=ifc_only,
            bc3_only=bc3_only,
            total_ifc_types=len(ifc_types),
            total_bc3_elements=len(bc3_elements)
        )
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        if not name:
            return ""
        
        # Remove special characters, convert to lowercase
        name = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s]', ' ', name.lower())
        # Remove multiple spaces
        name = ' '.join(name.split())
        return name
    
    def _calc_similarity(self, name1: str, name2: str) -> float:
        """Calculate Jaccard similarity between two names."""
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0
        
        # Remove common stopwords
        stopwords = {'de', 'la', 'el', 'en', 'con', 'para', 'por', 'a', 'y', 'o', 
                     'mm', 'cm', 'm', 'm2', 'm3', 'the', 'a', 'an'}
        words1 = words1 - stopwords
        words2 = words2 - stopwords
        
        if not words1 or not words2:
            return 0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0