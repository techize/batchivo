---
phase: 01-data-model-migration
plan: "02"
subsystem: database
tags: [sqlalchemy, alembic, pydantic, filament-type, spool, migration, two-tier-model]

# Dependency graph
requires:
  - phase: 01-data-model-migration
    provides: FilamentType model and schema (plan 01-01)

provides:
  - Updated Spool model with filament_type_id FK (RESTRICT) and is_labeled field
  - Stripped Spool of all type-level fields (brand, color, diameter, etc.)
  - Updated Spool schemas (SpoolBase, SpoolCreate, SpoolUpdate, SpoolResponse)
  - FilamentType registered in alembic/env.py for autogenerate
  - Merge migration unifying all 12 current alembic heads

affects: [01-03-data-migration, 01-04-api-endpoints, 01-05-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-tier filament model: FilamentType owns type definition, Spool is a per-unit record with FK"
    - "TYPE_CHECKING guard for SpoolResponse.filament_type to avoid circular imports"
    - "Alembic merge migration pattern: empty upgrade/downgrade with all heads in down_revision tuple"

key-files:
  created:
    - backend/alembic/versions/MERGE_filament_type_heads.py
  modified:
    - backend/app/models/spool.py
    - backend/app/schemas/spool.py
    - backend/alembic/env.py

key-decisions:
  - "ondelete=RESTRICT on filament_type_id FK prevents orphaned spools if a FilamentType is deleted"
  - "is_labeled defaults False so existing spools are treated as unlabeled until confirmed"
  - "SpoolResponse.filament_type uses Optional[FilamentTypeResponse] via TYPE_CHECKING guard — safe for parallel worktree execution where filament_type schema exists"
  - "All 12 current alembic heads verified from actual migration files before merge migration creation"

patterns-established:
  - "Merge migration is a pure merge point — upgrade/downgrade both pass, chains off all 12 heads"
  - "TYPE_CHECKING guard for cross-schema references to avoid runtime circular imports"

requirements-completed: [DATA-02, DATA-05]

# Metrics
duration: 12min
completed: 2026-05-19
---

# Phase 01 Plan 02: Spool Model Two-Tier Restructure Summary

**Spool model stripped of all type-level fields; filament_type_id FK (RESTRICT) and is_labeled added; SpoolBase/SpoolUpdate schemas updated; FilamentType registered in alembic env; merge migration unifying all 12 heads created**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-19T11:35:00Z
- **Completed:** 2026-05-19T11:47:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Removed 15 type-level columns from Spool model (brand, color, color_hex, finish, diameter, density, extruder_temp, bed_temp, translucent, glow, pattern, spool_type, notes, material_type_id, purchased_quantity, spools_remaining)
- Added filament_type_id FK to filament_types.id with ondelete=RESTRICT and is_labeled boolean (default False)
- Replaced material_type relationship with filament_type (lazy=joined) referencing FilamentType model
- Updated SpoolBase and SpoolUpdate schemas to match model; SpoolResponse nests FilamentTypeResponse via TYPE_CHECKING guard
- Registered FilamentType in alembic/env.py so autogenerate detects its table
- Created MERGE_filament_type_heads.py with all 12 verified head revision IDs in down_revision tuple

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Spool model — remove type fields, add filament_type_id and is_labeled** - `b1ba398` (feat)
2. **Task 2: Update Spool schemas + register FilamentType in env.py + create merge migration** - `a690bc7` (feat)

## Files Created/Modified

- `backend/app/models/spool.py` — Stripped to per-unit fields; filament_type_id FK + is_labeled added; filament_type relationship replacing material_type
- `backend/app/schemas/spool.py` — SpoolBase/SpoolCreate/SpoolUpdate reflect new model; SpoolResponse nests FilamentTypeResponse with TYPE_CHECKING guard
- `backend/alembic/env.py` — FilamentType import added for autogenerate support
- `backend/alembic/versions/MERGE_filament_type_heads.py` — Merge migration with all 12 current heads in down_revision

## Decisions Made

- Used `ondelete="RESTRICT"` on filament_type_id FK — prevents orphaned spools if a FilamentType is accidentally deleted (mitigates T-01-03)
- `is_labeled` defaults to False — conservative default means existing spools require explicit label confirmation
- SpoolResponse.filament_type annotated as `Optional["FilamentTypeResponse"]` via TYPE_CHECKING guard — enables parallel worktree execution where 01-01 may not have committed yet
- Confirmed all 12 head revision IDs from actual migration file content before creating merge migration — plan's candidate IDs matched actual

## Deviations from Plan

None — plan executed exactly as written. The Python runtime (poetry venv) was non-functional on this machine due to a deleted Python 3.14 installation, but verification was performed structurally via file content inspection, which confirmed all required fields, FK constraints, and ID counts.

## Issues Encountered

- Poetry venv depends on Python 3.14 which has been deleted from the system (`/opt/homebrew/Cellar/python@3.14/3.14.0` missing). Python import verification could not be run. Structural verification (grep, file content inspection) was used instead and confirmed all required changes are in place.

## Known Stubs

None — this plan makes no UI or data-rendering changes. The Spool API endpoints will fail at runtime until Plan 05 updates them (expected per plan design: schema changes first, API updates in Plan 05).

## Next Phase Readiness

- Plan 03 (data migration) can now be written: the Spool model has filament_type_id and the merge migration provides a single head to chain off
- Plan 04 (API endpoints) will update spools.py to use filament_type_id instead of flat material type fields
- The broken SpoolResponse.material_type_code/material_type_name references in spools.py are expected and will be fixed in Plan 04/05

## Self-Check

- backend/app/models/spool.py: contains `filament_type_id` and `is_labeled`; removed fields (`brand`, `color`, `material_type_id`) absent — VERIFIED
- backend/app/schemas/spool.py: `filament_type_id` and `is_labeled` in SpoolBase; `brand`, `material_type_id` absent — VERIFIED
- backend/alembic/env.py: `from app.models.filament_type import FilamentType` present — VERIFIED
- backend/alembic/versions/MERGE_filament_type_heads.py: 12 IDs in down_revision — VERIFIED
- Commits b1ba398 and a690bc7 exist — VERIFIED

## Self-Check: PASSED

---
*Phase: 01-data-model-migration*
*Completed: 2026-05-19*
