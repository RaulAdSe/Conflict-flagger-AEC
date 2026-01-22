# Performance Optimizations

This document describes the performance optimizations implemented to improve analysis speed and application startup time.

## Summary of Improvements

| Area | Before | After | Improvement |
|------|--------|-------|-------------|
| **Windows bundle size** | 155 MB | 96 MB | -38% |
| **Windows bundle files** | 1,096 | 462 | -58% |
| **macOS bundle size** | 222 MB | 206 MB | -7% |
| **IFC parsing (repeat)** | 2.8s | 0ms | Instant (cached) |
| **Matching** | 20ms | 11ms | -46% |
| **Report gen (complete)** | 6.0s | 3.5s | -42% |
| **Report gen (simple)** | 3.5s | 9ms | -99% |

## Build Size Optimizations

### Problem
The Windows executable built with Wine was taking 3-5 minutes to start due to:
- Large bundle size (155 MB)
- Many files to load (1,096 files in `_internal/`)
- Wine overhead when loading DLLs and initializing font cache

### Solution
Excluded unnecessary dependencies in `scripts/build/conflict_flagger.spec`:

```python
# Major exclusions (~60MB savings)
'numpy', 'numpy.libs',           # Pulled by ifcopenshell but unused
'shapely', 'Shapely.libs',       # Geometry library - unused
'PIL._avif', 'PIL._webp',        # Image codecs - unused
'ssl', '_ssl',                   # OpenSSL - unused

# Data file stripping (~4MB savings)
a.datas = [d for d in a.datas if 'tzdata' not in d[0]]  # Timezone data
a.datas = [d for d in a.datas if '/msgs/' not in d[0]]  # Locale messages
```

### .app Launch Fix
Added missing hidden imports for ifcopenshell transitive dependencies:
- `ifcopenshell.util.representation`
- `ifcopenshell.util.shape`
- `ifcopenshell.util.shape_builder`
- `ifcopenshell.util.placement`
- `ifcopenshell.api`

## IFC Parsing Cache

### Problem
IFC parsing takes ~2.8 seconds per file, with 78% of time in `ifcopenshell.open()` (file I/O).

### Solution
Added in-memory cache in `src/parsers/ifc_parser.py`:

```python
# Global cache for parsed IFC results
_IFC_CACHE: Dict[tuple, 'IFCParseResult'] = {}

def _get_cache_key(self, file_path: Path) -> tuple:
    """Cache key based on path, mtime, and size."""
    stat = file_path.stat()
    return (str(file_path.absolute()), stat.st_mtime, stat.st_size)
```

### Benefits
- First parse: ~2.8s (unchanged - I/O bound)
- Second parse: ~0ms (instant cache hit)
- Useful when comparing multiple BC3 files against the same IFC model

## Matcher Optimization

### Problem
Phase 2 (GUID matching) used nested loops O(n*m).
Phase 3 (name matching) called `_normalize_name()` repeatedly on same IFC types.

### Solution
In `src/matching/matcher.py`:

```python
# Phase 2: Build dict for O(1) GUID lookup
ifc_by_guid = {t.global_id: t for t in ifc_types}

# Phase 3: Pre-normalize IFC names
ifc_normalized_names = {t.global_id: self._normalize_name(t.name) for t in unmatched_ifc}
```

### Results
Matching time reduced by 46% (20ms → 11ms on SANT BOI baseline).

## Reporter Optimization

### Problem
Report generation was creating new `PatternFill`, `Font`, and `Alignment` objects for each of 200k+ cells. openpyxl's style hashing is expensive.

### Solution
Cache style objects in `src/reporting/reporter.py`:

```python
def __init__(self, config):
    # Pre-create and cache style objects
    self._fill_cache = {}
    self._header_font = Font(bold=True, color="FFFFFF", size=11)
    self._header_fill = PatternFill(...)
    self._cell_alignment = Alignment(vertical="center", wrap_text=True)

def _get_fill(self, color: str) -> PatternFill:
    """Get or create a cached PatternFill for the given color."""
    if color not in self._fill_cache:
        self._fill_cache[color] = PatternFill(...)
    return self._fill_cache[color]
```

### Results
Report generation reduced by 42% (6.0s → 3.5s on SANT BOI baseline).

## User Tips

1. **Use "Informe Simple" for quick checks** - Generates only summary and discrepancy sheets (9ms vs 3.5s)

2. **Same IFC file = instant** - If you analyze the same IFC with different BC3 files, parsing is cached

3. **Build for target platform** - Build on macOS for .app, use Wine for .exe only when needed

## Profiling

To profile the analysis pipeline, use:

```python
import time
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter

# Time each stage
t0 = time.perf_counter()
ifc_result = IFCParser().parse('file.ifc')
print(f'IFC Parse: {(time.perf_counter()-t0)*1000:.0f}ms')
# ... etc
```

## Future Optimizations

Potential improvements not yet implemented:

1. **Parallel IFC element processing** - Use ThreadPoolExecutor for property extraction
2. **Lazy report generation** - Skip elements summary sheet for simple reports
3. **Disk-based IFC cache** - Persist cache between sessions using pickle
4. **openpyxl write_only mode** - For very large reports (>10k rows)
