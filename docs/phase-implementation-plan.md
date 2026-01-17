# Phase Implementation Plan

> **Branch:** `master` (Phase 2 Complete)
> **Date:** 2026-01-17
> **Status:** ✅ Phase 1 Complete | ✅ Phase 2 Complete

---

## Overview

This document outlines the implementation plan to properly integrate Albert's matching improvements into the modular architecture, complete Phase 1 requirements, and prepare for Phase 2.

### Current Situation

Albert developed useful matching logic but broke the modular architecture by:
- Rewriting parsers inline (384 lines vs 897 in master)
- Removing phase system support
- Removing modern UI features (drag & drop)
- Not using the existing `src/matching/matcher.py`

**Goal:** Salvage the good ideas, integrate them properly, and complete all Phase 1 issues.

---

## Phase 1: Code & Quantity Matching

### 1.1 Integrate Description-Based Matching into `matcher.py`

**Issue:** #8 (Check matching)
**Status:** To Do
**Priority:** HIGH

Albert's key contribution is Jaccard similarity matching when codes don't match directly. This needs to be added as a 4th matching strategy.

#### Current Matching Strategies (in `src/matching/matcher.py`)
1. `TAG` - Tag ↔ Code (exact match)
2. `GUID` - GlobalId ↔ Tipo IfcGUID
3. `NAME` - Family + Type name matching

#### New Strategy to Add
4. `DESCRIPTION` - Jaccard similarity on descriptions

#### Implementation Tasks

- [ ] **1.1.1** Add `MatchMethod.DESCRIPTION` to enum in `matcher.py`
- [ ] **1.1.2** Port `normalize_desc()` function from Albert's code
- [ ] **1.1.3** Port `calc_similarity()` (Jaccard) function
- [ ] **1.1.4** Add `_match_by_description()` method to `Matcher` class
- [ ] **1.1.5** Integrate as Strategy 4 in `match()` method
- [ ] **1.1.6** Add confidence score (0.5-0.8 based on similarity)
- [ ] **1.1.7** Add tests for description matching

#### Code to Port (from Albert's `app_comparator.py`)

```python
def normalize_desc(desc):
    """Normaliza descripción para comparación"""
    if not desc:
        return ""
    desc = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s]', ' ', desc.lower())
    desc = ' '.join(desc.split())
    return desc

def calc_similarity(desc1, desc2):
    """Calcula similitud entre dos descripciones (0-1)"""
    words1 = set(normalize_desc(desc1).split())
    words2 = set(normalize_desc(desc2).split())

    if not words1 or not words2:
        return 0

    stopwords = {'de', 'la', 'el', 'en', 'con', 'para', 'por', 'a', 'y', 'o', 'mm', 'cm', 'm', 'm2', 'm3'}
    words1 = words1 - stopwords
    words2 = words2 - stopwords

    if not words1 or not words2:
        return 0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0
```

---

### 1.2 Add Element Ignore Filter

**Issue:** #11 (Sin modelar y sin presupuestar fuera de discrepancias)
**Status:** To Do
**Priority:** MEDIUM

Albert's ignore list filters non-comparable elements (views, sheets, rooms, etc.).

#### Implementation Tasks

- [ ] **1.2.1** Create `src/matching/filters.py` module
- [ ] **1.2.2** Port `is_ignored_item()` function with ignore terms list
- [ ] **1.2.3** Apply filter in `Matcher.match()` before matching
- [ ] **1.2.4** Add configuration option to enable/disable filtering
- [ ] **1.2.5** Add tests for filter

#### Ignore Terms (from Albert)

```python
IGNORE_TERMS = [
    "información", "project info", "plano", "sheet", "vista", "view",
    "zona de", "climatización", "topografía", "habitaciones", "rooms",
    "áreas", "areas", "ocupacion", "sup.libre", "sup.construida",
    "almacén", "salón", "cocina", "aseo", "archivo", "circulación",
    "área de trabajo", "sala de reuniones", "dep. limpieza",
    "aseos femeninos", "aseos masculinos",
    "aberturas", "hueco", "opening", "void", "corte", "líneas", "lines",
    "materiales", "materials", "tubería", "pipe", "segmentos",
    "system panel", "empty panel"
]
```

---

### 1.3 Update Reporter for Phase 1

**Issues:** #7 (Restrict report), #9 (Errors first), #11 (Separate sheets)
**Status:** To Do
**Priority:** HIGH

#### Current Report Structure
- Single "Discrepancias" sheet with all conflict types

#### Required Phase 1 Report Structure

| Sheet | Content | Color |
|-------|---------|-------|
| **Discrepancias** | Errors only (code/qty mismatch) | Red/Orange |
| **Coincidencias** | Matched items (OK) | Green |
| **Sin Presupuestar** | IFC items not in BC3 | Yellow |
| **Sin Modelar** | BC3 items not in IFC | Yellow |

#### Phase 1 Columns (Issue #7)
Only show:
1. `CODIGO_BC3`
2. `CODIGO_IFC`
3. `DESCRIPCION` (name)
4. `UNIDAD` (unit)
5. `CANT_BC3` (quantity BC3)
6. `CANT_IFC` (quantity IFC)
7. `ESTADO` (status)
8. `DETALLE` (detail message)

#### Implementation Tasks

- [ ] **1.3.1** Update `PhaseConfig` for `QUICK_CHECK` with correct sheets
- [ ] **1.3.2** Modify `Reporter` to sort errors first (Issue #9)
- [ ] **1.3.3** Create separate sheets for Sin Presupuestar / Sin Modelar
- [ ] **1.3.4** Implement color coding:
  - Orange: `CODIGO_DIFERENTE` (matched by description, different codes)
  - Red: `CANTIDAD_DIFERENTE` (quantity mismatch)
  - Green: `OK` (matches)
- [ ] **1.3.5** Remove yellow from discrepancies (per Issue #9 comment)
- [ ] **1.3.6** Add tests for reporter output

---

### 1.4 Add Quantity Comparison to Comparator

**Issue:** #12 (Test phase 1 reporter errors)
**Status:** To Do
**Priority:** HIGH

Currently comparator focuses on property mismatches. Phase 1 needs:
- Code mismatch detection
- Quantity mismatch detection
- Unit mismatch detection

#### Implementation Tasks

- [ ] **1.4.1** Add `ConflictType.CODE_MISMATCH` for description-matched items
- [ ] **1.4.2** Add `ConflictType.UNIT_MISMATCH` for unit differences
- [ ] **1.4.3** Ensure quantity comparison works with tolerance
- [ ] **1.4.4** Update `_compare_pair()` to check these in Phase 1 mode
- [ ] **1.4.5** Test with `MODELO ERRONEO.bc3` test data

---

### 1.5 Restore App Features

**Issues:** #13 (Duplicate instance bug), #14 (Open Excel automatically)
**Status:** To Do
**Priority:** LOW

#### Implementation Tasks

- [ ] **1.5.1** Restore `app_comparator.py` from master (with modern UI)
- [ ] **1.5.2** Verify duplicate instance fix works (Issue #13 - already fixed in master)
- [ ] **1.5.3** Add cross-platform Excel opening (Issue #14)
  ```python
  import subprocess
  import platform

  def open_file(filepath):
      if platform.system() == 'Darwin':  # macOS
          subprocess.call(['open', filepath])
      elif platform.system() == 'Windows':
          os.startfile(filepath)
      else:  # Linux
          subprocess.call(['xdg-open', filepath])
  ```
- [ ] **1.5.4** Test on macOS and Windows

---

### 1.6 Test Phase 1 End-to-End

**Issue:** #12 (Produce test data and test)
**Status:** To Do
**Priority:** HIGH

#### Test Data Available
- `GUIA MODELADO V2.ifc` - Baseline IFC (correct)
- `GUIA MODELADO V2 2025-12-18 06-47-01.bc3` - Baseline BC3 (correct)
- `MODELO ERRONEO.bc3` - Modified BC3 with intentional errors

#### Intentional Errors in `MODELO ERRONEO.bc3`
| Type | Original | Modified |
|------|----------|----------|
| Quantity | 24 | 20 |
| Code | 171671 | 171999 |
| Code | 378878 | 378111 |
| Code | 378892 | 378000 |
| Quantity | 2 | 5 |

#### Implementation Tasks

- [ ] **1.6.1** Run comparison: `GUIA MODELADO V2.ifc` + `MODELO ERRONEO.bc3`
- [ ] **1.6.2** Verify all 5 intentional errors are detected
- [ ] **1.6.3** Verify description matching finds code 171999 ↔ 171671
- [ ] **1.6.4** Verify quantity differences are flagged
- [ ] **1.6.5** Document results

---

## Phase 2: Property Mismatch (Spatial)

**Issue:** #10 (Restrict property mismatch to h w d)
**Status:** ✅ Complete (PR #20)
**Priority:** DONE

### 2.1 Restrict Property Comparison to Dimensions

Phase 2 focuses only on spatial properties:
- **h** (height / altura)
- **b** (width / anchura)
- **d** (depth / profundidad)
- **length** (longitud)
- **thickness** (grosor / espesor)

#### Implementation (commit 4992115)

Added two property lists to `comparator.py`:

```python
# Spatial properties only (used by FULL_ANALYSIS phase)
SPATIAL_PROPERTIES = [
    ('h', 'h'),
    ('b', 'b'),
    ('d', 'd'),
    ('Anchura', 'width'),
    ('Altura', 'height'),
    ('Profundidad', 'depth'),
    ('Grosor', 'thickness'),
    ('Longitud', 'length'),
    ('Espesor', 'thickness'),
]

# All properties including material and thermal
ALL_PROPERTIES = [
    # ...spatial + Material + thermal properties
]
```

Added `property_list` field to `PhaseConfig`:
- `"spatial"` - Only compare h/w/d properties (default)
- `"all"` - Compare all properties including material and thermal

#### Implementation Tasks

- [x] **2.1.1** Create `SPATIAL_PROPERTIES` list with only spatial properties
- [x] **2.1.2** Add `property_list` field to `PhaseConfig`
- [x] **2.1.3** Update `FULL_ANALYSIS` to use `property_list="spatial"`
- [x] **2.1.4** Update `Comparator.compare()` to select property list from config
- [x] **2.1.5** Update `_compare_pair()` to use selected property list
- [x] **2.1.6** Add tests for Phase 2 property list selection (4 tests)

---

## Git Workflow & Branching Strategy

### Branch Overview

```
master (stable)
│
├── feature/phase1-matching ← Sprint 1 (from master, NOT from Albert's branch)
│   ├── commit: "feat(matcher): add description-based matching strategy"
│   ├── commit: "feat(matcher): add element ignore filter"
│   └── commit: "test(matcher): add tests for description matching"
│
├── feature/phase1-reporter ← Sprint 2 (from feature/phase1-matching after merge)
│   ├── commit: "feat(comparator): add code/unit/quantity mismatch types"
│   ├── commit: "feat(reporter): restructure for Phase 1 output"
│   └── commit: "test: verify MODELO ERRONEO.bc3 errors detected"
│
├── feature/phase1-ui ← Sprint 3 (from feature/phase1-reporter after merge)
│   ├── commit: "feat(app): restore modern UI from master"
│   ├── commit: "feat(app): add cross-platform Excel auto-open"
│   └── commit: "test: end-to-end Phase 1 validation"
│
└── feature/phase2-properties ← Sprint 4 (from master after Phase 1 complete)
    ├── commit: "feat(comparator): restrict to spatial properties (h/w/d)"
    └── commit: "test: verify dimension mismatch detection"
```

### Why NOT Continue from `app-comparator-matching-v3`

Albert's branch has broken architecture:
- `app_comparator.py` was rewritten with inline parsers
- Modern UI features removed
- Phase system removed

**Strategy:** Start fresh from `master`, cherry-pick only the algorithm ideas (not code).

---

### Step-by-Step Git Commands

#### Initial Setup (Before Sprint 1)

```bash
# Ensure we have latest master
git checkout master
git pull origin master

# Create Sprint 1 branch FROM MASTER
git checkout -b feature/phase1-matching

# Keep Albert's branch for reference (don't delete)
# We'll manually port his algorithms, not merge his code
```

#### Sprint 1 Commits

```bash
# After implementing description matching in matcher.py
git add src/matching/matcher.py
git commit -m "feat(matcher): add description-based matching strategy

- Add MatchMethod.DESCRIPTION enum value
- Port Jaccard similarity algorithm from Albert's work
- Add normalize_desc() and calc_similarity() functions
- Integrate as 4th matching strategy after NAME matching
- Add confidence scoring based on similarity threshold

Closes #8"

# After creating filters.py
git add src/matching/filters.py src/matching/__init__.py
git commit -m "feat(matcher): add element ignore filter

- Create filters.py with IGNORE_TERMS list
- Add is_ignored_item() function
- Filter out non-comparable elements (views, rooms, areas, etc.)

Relates to #11"

# After adding tests
git add tests/test_matcher.py tests/test_filters.py
git commit -m "test(matcher): add tests for description matching and filters"

# Push and create PR
git push -u origin feature/phase1-matching
gh pr create --title "Phase 1: Description-based matching" --body "..."
```

#### Sprint 2 Commits

```bash
# After Sprint 1 PR is merged
git checkout master
git pull origin master
git checkout -b feature/phase1-reporter

# After adding conflict types
git add src/comparison/comparator.py
git commit -m "feat(comparator): add code/unit/quantity mismatch detection

- Add ConflictType.CODE_MISMATCH for description-matched items
- Add ConflictType.UNIT_MISMATCH for unit differences
- Update _compare_pair() for Phase 1 mode

Closes #12"

# After updating reporter
git add src/reporting/reporter.py src/phases/config.py
git commit -m "feat(reporter): restructure output for Phase 1

- Add separate sheets: Discrepancias, Coincidencias, Sin Presupuestar, Sin Modelar
- Sort errors first in Discrepancias sheet
- Update color coding (orange=code diff, red=qty diff)
- Remove yellow from main discrepancies

Closes #7, #9, #11"

# After testing
git add tests/
git commit -m "test: verify all 5 MODELO ERRONEO.bc3 errors detected"

# Push and create PR
git push -u origin feature/phase1-reporter
gh pr create --title "Phase 1: Reporter restructure" --body "..."
```

#### Sprint 3 Commits

```bash
# After Sprint 2 PR is merged
git checkout master
git pull origin master
git checkout -b feature/phase1-ui

# Restore app_comparator.py from master (it has the good UI)
# Since we're on master-based branch, it should already be correct
# Just add the Excel auto-open feature

git add src/app_comparator.py
git commit -m "feat(app): add cross-platform Excel auto-open

- Add open_file() utility for macOS/Windows/Linux
- Open Excel report automatically after comparison
- Verify duplicate instance prevention still works

Closes #13, #14"

# Final validation
git add tests/
git commit -m "test: end-to-end Phase 1 validation complete"

# Push and create PR
git push -u origin feature/phase1-ui
gh pr create --title "Phase 1: UI polish and final validation" --body "..."
```

#### Sprint 4 Commits (Phase 2)

```bash
# After Phase 1 is complete and merged
git checkout master
git pull origin master
git checkout -b feature/phase2-properties

# Implement spatial property comparison
git add src/comparison/comparator.py src/phases/config.py
git commit -m "feat(comparator): restrict Phase 2 to spatial properties (h/w/d)

- Create SPATIAL_PROPERTIES list
- Update PhaseConfig.FULL_ANALYSIS to use spatial-only
- Skip material and thermal properties

Closes #10"

# Push and create PR
git push -u origin feature/phase2-properties
gh pr create --title "Phase 2: Spatial property mismatch" --body "..."
```

---

### Commit Message Convention

```
<type>(<scope>): <description>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `test` - Adding tests
- `docs` - Documentation
- `refactor` - Code refactoring

**Scopes:**
- `matcher` - Matching logic
- `comparator` - Comparison logic
- `reporter` - Excel output
- `app` - UI/Application
- `parser` - IFC/BC3 parsing

**Footer:**
- `Closes #X` - Closes issue
- `Relates to #X` - Related issue

---

### PR Strategy

| Sprint | Branch | PR Title | Closes Issues |
|--------|--------|----------|---------------|
| 1 | `feature/phase1-matching` | Phase 1: Description-based matching | #8 |
| 2 | `feature/phase1-reporter` | Phase 1: Reporter restructure | #7, #9, #11, #12 |
| 3 | `feature/phase1-ui` | Phase 1: UI polish | #13, #14 |
| 4 | `feature/phase2-properties` | Phase 2: Spatial properties | #10 |

---

### What Happens to `app-comparator-matching-v3`?

**Option A (Recommended):** Leave as historical reference
```bash
# Don't delete, just leave it
# It documents Albert's approach for future reference
```

**Option B:** Archive it
```bash
git tag archive/albert-matching-v3 origin/app-comparator-matching-v3
git push origin archive/albert-matching-v3
# Then delete branch if desired
```

---

## Implementation Order

### Sprint 1: Core Matching (Phase 1.1 - 1.2)
1. Integrate description matching into `matcher.py`
2. Add element ignore filter
3. Write tests

### Sprint 2: Reporting (Phase 1.3 - 1.4)
1. Update reporter for Phase 1 structure
2. Add quantity/code/unit mismatch detection
3. Test with MODELO ERRONEO.bc3

### Sprint 3: Polish (Phase 1.5 - 1.6)
1. Restore modern UI from master
2. Fix Excel auto-open
3. End-to-end testing
4. Close Phase 1 issues

### Sprint 4: Phase 2
1. Implement spatial property comparison
2. Test and document

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/matching/matcher.py` | MODIFY | Add description matching strategy |
| `src/matching/filters.py` | CREATE | Element ignore filter |
| `src/comparison/comparator.py` | MODIFY | Add code/unit mismatch types |
| `src/reporting/reporter.py` | MODIFY | Phase 1 report structure |
| `src/phases/config.py` | MODIFY | Update phase configurations |
| `src/app_comparator.py` | RESTORE | From master, add Excel open |
| `tests/test_matcher.py` | MODIFY | Add description matching tests |
| `tests/test_filters.py` | CREATE | Filter tests |

---

## Success Criteria

### Phase 1 Complete When:
- [ ] All 5 errors in `MODELO ERRONEO.bc3` are detected
- [ ] Description matching finds items with different codes
- [ ] Report shows errors first, matches in separate sheet
- [ ] Sin Presupuestar / Sin Modelar in dedicated sheets
- [ ] Excel opens automatically after comparison
- [ ] No duplicate app instances
- [ ] Issues #7, #8, #9, #11, #12, #13, #14 closed

### Phase 2 Complete When:
- [x] Spatial property (h/w/d) mismatches detected
- [x] Non-spatial properties ignored (via `property_list="spatial"`)
- [x] Issue #10 closed (PR #20)

---

## References

- GitHub Issues: https://github.com/RaulAdSe/Conflict-flagger-AEC/issues
- Test Data: `/Users/rauladell/Conflict-flagger-AEC/data/input/`
- Architecture Docs: `/Users/rauladell/Conflict-flagger-AEC/docs/arquitectura.md`
