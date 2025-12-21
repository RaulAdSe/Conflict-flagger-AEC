# Matcher

## Description

The Matcher pairs elements between the IFC model and BC3 budget using multiple strategies. It's the central component that links both data sources.

## Location

```
src/matching/matcher.py
```

## Main Classes

### MatchMethod (Enum)

```python
class MatchMethod(Enum):
    GUID = "guid"           # By IFC GlobalId
    TAG = "tag"             # By Tag/Revit ID
    NAME = "name"           # By type name
    TYPE_NAME = "type_name" # By family:type name
    NONE = "none"           # Not matched
```

### MatchStatus (Enum)

```python
class MatchStatus(Enum):
    MATCHED = "matched"     # Successfully matched
    IFC_ONLY = "ifc_only"   # Only exists in IFC
    BC3_ONLY = "bc3_only"   # Only exists in BC3
```

### MatchedPair

```python
@dataclass
class MatchedPair:
    status: MatchStatus         # Match status
    method: MatchMethod         # Method used
    ifc_type: Optional[IFCType] # IFC type (if exists)
    bc3_element: Optional[BC3Element]  # BC3 element (if exists)
    match_key: Optional[str]    # Match key
    confidence: float = 1.0     # Confidence level (0-1)

    @property
    def code(self) -> str:
        """Element code."""
        if self.bc3_element:
            return self.bc3_element.code
        if self.ifc_type:
            return self.ifc_type.tag or self.ifc_type.global_id
        return ""

    @property
    def name(self) -> str:
        """Element name."""
        if self.ifc_type:
            return self.ifc_type.name
        if self.bc3_element:
            return self.bc3_element.description
        return ""
```

### MatchResult

```python
@dataclass
class MatchResult:
    matched: list[MatchedPair]      # Matched elements
    ifc_only: list[MatchedPair]     # IFC only
    bc3_only: list[MatchedPair]     # BC3 only
    total_ifc_types: int            # Total IFC types
    total_bc3_elements: int         # Total BC3 elements
    match_count: int                # Number matched

    @property
    def match_rate(self) -> float:
        """Match percentage."""
        total = self.total_ifc_types + self.total_bc3_elements
        if total == 0:
            return 0.0
        return (self.match_count * 2 / total) * 100
```

## Basic Usage

```python
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher

# Parse files
ifc_parser = IFCParser()
bc3_parser = BC3Parser()

ifc_result = ifc_parser.parse("model.ifc")
bc3_result = bc3_parser.parse("budget.bc3")

# Match
matcher = Matcher()
match_result = matcher.match(ifc_result, bc3_result)

# Results
print(f"Matched: {len(match_result.matched)}")
print(f"IFC only: {len(match_result.ifc_only)}")
print(f"BC3 only: {len(match_result.bc3_only)}")
print(f"Match rate: {match_result.match_rate:.1f}%")
```

## Matching Strategies

### 1. By GUID (High Priority)

Searches for IFC GlobalId in BC3 properties.

```
IFC: GlobalId = "3n$x9KvBD0..."
BC3: GUID_IFC = "3n$x9KvBD0..."
→ MATCH (confidence: 1.0)
```

**Advantages:**
- Guaranteed unique identification
- No ambiguity

**Requirements:**
- BC3 must have GUID stored
- Correct export from Revit to Presto

### 2. By Tag (High Priority)

Uses Revit Tag (Element ID) as key.

```
IFC: Tag = "350147"
BC3: Code = "350147"
→ MATCH (confidence: 1.0)
```

**Advantages:**
- Simple and direct
- Works with Revit → Presto workflows

**Requirements:**
- Maintain code consistency

### 3. By Name (Medium Priority)

Compares type names.

```
IFC: Name = "Column:600x600"
BC3: Description = "Concrete column 600x600"
→ MATCH (confidence: 0.8)
```

**Advantages:**
- Works without specific IDs
- Useful fallback

**Disadvantages:**
- May have false positives
- Sensitive to name variations

## Configuration

```python
matcher = Matcher(
    match_by_guid=True,    # Use GUID (default: True)
    match_by_tag=True,     # Use Tag (default: True)
    match_by_name=True,    # Use name (default: True)
    min_confidence=0.7     # Minimum confidence (default: 0.7)
)
```

### Disable Strategies

```python
# Only match by GUID and Tag
matcher = Matcher(match_by_name=False)

# Only match by Tag
matcher = Matcher(match_by_guid=False, match_by_name=False)
```

## Matching Order

```
1. Try by GUID
   └─ If found → MATCH (confidence: 1.0)

2. Try by Tag
   └─ If found → MATCH (confidence: 1.0)

3. Try by Name
   └─ If similarity > 0.7 → MATCH (confidence: similarity)

4. No match
   └─ Mark as IFC_ONLY or BC3_ONLY
```

## Result Analysis

### Matched Elements

```python
for pair in match_result.matched:
    print(f"{pair.code}: {pair.method.value}")
    print(f"  IFC: {pair.ifc_type.name}")
    print(f"  BC3: {pair.bc3_element.description}")
    print(f"  Confidence: {pair.confidence:.0%}")
```

### Unbudgeted Elements

```python
for pair in match_result.ifc_only:
    print(f"Not budgeted: {pair.ifc_type.name}")
    print(f"  Class: {pair.ifc_type.ifc_class}")
    print(f"  Tag: {pair.ifc_type.tag}")
```

### Unmodeled Elements

```python
for pair in match_result.bc3_only:
    print(f"Not modeled: {pair.bc3_element.description}")
    print(f"  Code: {pair.bc3_element.code}")
    print(f"  Price: {pair.bc3_element.price}")
```

## Statistics

```python
summary = match_result.summary()

print(f"Total IFC: {summary['total_ifc_types']}")
print(f"Total BC3: {summary['total_bc3_elements']}")
print(f"Matched: {summary['matched']}")
print(f"IFC only: {summary['ifc_only']}")
print(f"BC3 only: {summary['bc3_only']}")
print(f"Rate: {summary['match_rate']:.1f}%")
```

## Best Practices

### 1. Maintain Code Consistency

```
Revit Element ID  →  BC3 Code
     350147       →    350147
```

### 2. Export GUID

Configure Presto to save IFC GUID.

### 3. Review Unmatched

```python
# Review unmatched elements
if len(match_result.ifc_only) > 10:
    print("WARNING: Many unbudgeted elements")

if len(match_result.bc3_only) > 10:
    print("WARNING: Many unmodeled items")
```

## Troubleshooting

### Low Match Rate

**Common causes:**
1. Different codes between IFC and BC3
2. GUID not exported correctly
3. Very different names

**Solution:**
```python
# Analyze matching methods
methods = {}
for pair in match_result.matched:
    method = pair.method.value
    methods[method] = methods.get(method, 0) + 1

print("Methods used:", methods)
```

### False Positives

**Causes:**
- Similar names for different elements
- Reused codes

**Solution:**
```python
# Increase minimum confidence
matcher = Matcher(min_confidence=0.9)

# Disable name matching
matcher = Matcher(match_by_name=False)
```
