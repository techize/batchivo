---
phase: 01-data-model-migration
plan: "01"
subsystem: backend/models,backend/schemas
tags: [filament-type, orm-model, pydantic-schema, data-model]
dependency_graph:
  requires: []
  provides:
    - FilamentType ORM model (backend/app/models/filament_type.py)
    - FilamentType Pydantic schema hierarchy (backend/app/schemas/filament_type.py)
  affects:
    - backend/app/models/
    - backend/app/schemas/
tech_stack:
  added: []
  patterns:
    - SQLAlchemy 2.0 mapped_column with comment= convention
    - Pydantic v2 Base/Create/Update/Response/ListResponse hierarchy
    - UUIDMixin + TimestampMixin from app.models.base
key_files:
  created:
    - backend/app/models/filament_type.py
    - backend/app/schemas/filament_type.py
  modified: []
decisions:
  - "FilamentTypeUpdate does not inherit FilamentTypeBase — all fields re-declared Optional to avoid accidental required fields on PATCH"
  - "material_type_code and material_type_name are plain schema fields on FilamentTypeResponse, populated by API layer from lazy=joined relationship"
  - "brand and color are NOT NULL on the ORM model, matching D-04 deduplication key requirement"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-19"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 01 Plan 01: FilamentType Model and Schema Hierarchy Summary

**One-liner:** SQLAlchemy FilamentType model with all D-01 fields and a five-class Pydantic schema hierarchy including all-optional Update and from_attributes Response.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create FilamentType SQLAlchemy model | c7d8eec | backend/app/models/filament_type.py |
| 2 | Create FilamentType Pydantic schema hierarchy | c7d8eec | backend/app/schemas/filament_type.py |

## What Was Built

**FilamentType ORM model** (`backend/app/models/filament_type.py`):

- `class FilamentType(Base, UUIDMixin, TimestampMixin)` with `__tablename__ = "filament_types"`
- All D-01 fields: `brand` (String 100, NOT NULL), `color` (String 50, NOT NULL), `color_hex`, `finish`, `pattern`, `spool_type`, `diameter` (Numeric 4,2, default 1.75), `density`, `extruder_temp`, `bed_temp`, `translucent`, `glow`, `notes`, `has_sample`
- `tenant_id` FK to `tenants.id` with `ondelete="CASCADE"`, indexed
- `material_type_id` FK to `material_types.id`, indexed
- `material_type` relationship: `Mapped["MaterialType"]` with `lazy="joined"`
- `spools` back-reference: `Mapped[list["Spool"]]` with `lazy="select"` and `back_populates="filament_type"`
- Every `mapped_column` has a `comment=` kwarg matching the project convention
- No circular imports — `MaterialType` and `Spool` referenced as forward-reference strings only

**FilamentType Pydantic schemas** (`backend/app/schemas/filament_type.py`):

- `FilamentTypeBase(BaseModel)`: brand/color required with min_length=1 validators, diameter=1.75 default, has_sample=False default
- `FilamentTypeCreate(FilamentTypeBase)`: pass-through
- `FilamentTypeUpdate(BaseModel)`: all fields Optional with same validators; includes `material_type_id: Optional[UUID] = None`; does NOT inherit from FilamentTypeBase
- `FilamentTypeResponse(FilamentTypeBase)`: adds `id`, `tenant_id`, `created_at`, `updated_at`, `material_type_code`, `material_type_name`; `model_config = ConfigDict(from_attributes=True)`
- `FilamentTypeListResponse(BaseModel)`: `total`, `filament_types: list[FilamentTypeResponse]`, `page=1`, `page_size=20`

## Decisions Made

1. **FilamentTypeUpdate does not inherit FilamentTypeBase** — re-declares all fields as Optional to avoid required-field bleed-through on PATCH requests. Matches the `SpoolUpdate(BaseModel)` pattern in the codebase.
2. **material_type_code/name as plain schema fields** — populated by the API layer from the `lazy="joined"` relationship; not ORM validators. Avoids coupling schema to ORM.
3. **brand and color NOT NULL** — deduplication key per D-04; empty-string prevented by `min_length=1` validators (T-01-02 mitigation).

## Deviations from Plan

### Environment Issue (Non-Blocking)

**Poetry venv broken — automated verification skipped**

- **Found during:** Task 1 verification step
- **Issue:** Poetry's virtualenv references Python 3.14.0 (`/opt/homebrew/Cellar/python@3.14/3.14.0`) which brew upgraded to 3.14.4, removing the old dylib. Runtime import via `poetry run python` exits with `dyld[...] Library not loaded`.
- **Impact on this plan:** None — the files were verified via AST syntax check and structural grep. All D-01 fields confirmed present. All schema classes confirmed present with correct inheritance and `from_attributes=True`.
- **Resolution needed:** `poetry env remove --all && poetry install` to rebuild the venv against Python 3.14.4. Out of scope for this plan.
- **Scope:** Pre-existing environment issue; not caused by any change in this plan.

## Known Stubs

None — this plan creates pure type definitions with no data-flow to UI rendering.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary crossings introduced. The `tenant_id` FK with CASCADE is in place per T-01-01.

## Self-Check

- [x] `backend/app/models/filament_type.py` exists
- [x] `backend/app/schemas/filament_type.py` exists
- [x] Commit `c7d8eec` exists with both files staged
- [x] All D-01 fields confirmed in model via structural grep
- [x] All five schema classes present with correct inheritance
- [x] No files accidentally deleted in commit (2 insertions, 0 deletions)

## Self-Check: PASSED
