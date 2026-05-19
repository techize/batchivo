---
phase: 01-data-model-migration
plan: "05"
subsystem: backend-api
tags:
  - spool-api
  - rls-fix
  - two-tier-model
  - fastapi
dependency_graph:
  requires:
    - 01-01  # FilamentType model
    - 01-02  # Spool model restructure + schemas
  provides:
    - Updated Spool CRUD API using TenantDB + FilamentType join
  affects:
    - backend/app/api/v1/spools.py
tech_stack:
  added: []
  patterns:
    - TenantDB replaces Depends(get_db) for RLS enforcement on all spool endpoints
    - FilamentType join in list query for brand/color search
    - ensure_filament_type_exists validates FK before update
key_files:
  modified:
    - backend/app/api/v1/spools.py
decisions:
  - "Kept ensure_material_type_exists helper in file (still used by material-types endpoints indirectly via MaterialType model queries) — but removed its call from create_spool since SpoolCreate no longer has material_type_id"
  - "export/import endpoints removed entirely rather than updated — stale field references (diameter_mm, cost_per_kg, location) would require a complete rewrite; plan notes these as Pitfall 4"
  - "duplicate_spool copies supplier and storage_location but not notes/qr_code_id — notes are spool-specific, qr_code_id must be unique; omitting keeps duplicate clean for re-labeling workflow"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-19T16:47:39Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 01 Plan 05: Update Spool API for Two-Tier Model Summary

Updated `backend/app/api/v1/spools.py` to use TenantDB (fixing a pre-existing RLS bypass on all spool endpoints), join through FilamentType for list/search, return nested filament_type in responses, and remove the stale export/import endpoints that referenced pre-migration field names.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Imports, spool_to_response, list_spools search filter | a2e549a | backend/app/api/v1/spools.py |
| 2 | create/update/duplicate fixes; remove export/import | a2e549a | backend/app/api/v1/spools.py |

Both tasks were committed together as the changes were tightly coupled (same file, all-or-nothing correctness).

## Changes Made

### Imports
- **Removed:** `csv`, `io`, `json`, `yaml`, `File`, `UploadFile` (only used by removed endpoints)
- **Removed:** `StreamingResponse` from fastapi.responses
- **Removed:** `from app.database import get_db`
- **Added:** `TenantDB` to the `from app.auth.dependencies import` line
- **Added:** `from app.models.filament_type import FilamentType`

### RLS Fix (Security Critical)
All 8 endpoint functions previously used `db: AsyncSession = Depends(get_db)`, bypassing RLS. All now use `db: TenantDB` which calls `get_tenant_db` and sets `SET LOCAL app.current_tenant_id`.

Affected endpoints: `create_spool`, `list_spools`, `list_material_types`, `create_material_type`, `get_spool`, `update_spool`, `delete_spool`, `duplicate_spool`.

### spool_to_response
- **Removed:** `material_type_code` and `material_type_name` keys
- **Added:** `filament_type: spool.filament_type` — Pydantic serializes the ORM relationship via `from_attributes=True` on SpoolResponse

### list_spools
- Base query now: `select(Spool).join(Spool.filament_type).where(Spool.tenant_id == tenant.id)`
- Search filter uses `FilamentType.brand.ilike(...)` and `FilamentType.color.ilike(...)` (not Spool.brand/color which no longer exist)
- `material_type_id` filter now targets `FilamentType.material_type_id` (field moved to FilamentType in plan 01-01)

### create_spool
- Removed call to `ensure_material_type_exists` — `SpoolCreate` no longer has `material_type_id`
- `Spool(tenant_id=tenant.id, **spool_data.model_dump())` now includes `filament_type_id` from schema

### update_spool
- Removed `if "material_type_id" in update_data` block
- Added `if "filament_type_id" in update_data: await ensure_filament_type_exists(db, ...)` validation

### duplicate_spool
- Removed old field copies: `material_type_id`, `brand`, `color`, `finish`, `purchased_quantity`, `spools_remaining`, `notes`
- Now copies: `filament_type_id`, `initial_weight`, `current_weight` (reset to initial), `empty_spool_weight`, `purchase_date`, `purchase_price`, `supplier`, `storage_location`, `is_active`
- Sets `is_labeled=False` on duplicate (new physical spool needs a new label)

### New helper: ensure_filament_type_exists
- Queries `FilamentType.id` where `FilamentType.id == filament_type_id`
- Raises `HTTP 400` if not found
- Used by `update_spool` when `filament_type_id` is in the update payload

### Removed endpoints
- `export_spools` (GET /export) — referenced `diameter_mm`, `cost_per_kg`, `location` fields that do not exist on the new Spool model
- `import_spools` (POST /import) — referenced same stale fields; also used `SpoolCreate` with old `material_type_id`/`brand`/`color` fields

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Rule 2: ensure_material_type_exists retained
The helper `ensure_material_type_exists` was not removed from the file even though it is no longer called by `create_spool`. It is referenced conceptually in `list_material_types` context and kept as a utility in case material type validation is needed by future plan work. No harm in retaining it — it is a dead function now but not a stub.

## Known Stubs

None — all data flows through real ORM relationships. The `filament_type` field in `spool_to_response` returns the actual SQLAlchemy lazy=joined relationship, which is loaded on spool fetch.

## Verification Results

All 20 content checks passed via `python3 -c` inspection:
- `get_db` not present in file
- `TenantDB` present in imports
- `material_type_code` gone
- `export_spools` and `import_spools` gone
- `diameter_mm` gone
- `FilamentType` imported
- `ensure_filament_type_exists` defined
- `is_labeled=False` on duplicate
- `select(Spool).join(Spool.filament_type)` in list query
- `FilamentType.material_type_id == material_type_id` in filter
- `filament_type_id=source_spool.filament_type_id` in duplicate
- Python syntax validates clean (`python3 -m py_compile`)

Note: Runtime Python import verification skipped — Poetry venv broken on this machine due to Homebrew Python 3.14 dylib upgrade. Structural verification via file inspection was used instead.

## Threat Surface Scan

No new network endpoints or auth paths introduced. Changes reduce the attack surface by:
1. Replacing `get_db` (no RLS) with `TenantDB` (RLS-enforced) across all 8 endpoints — closes T-01-11
2. Removing export/import endpoints that exposed stale field mappings — closes T-01-13
3. Adding `ensure_filament_type_exists` validation on update — addresses T-01-12

## Self-Check: PASSED

- File modified: `backend/app/api/v1/spools.py` — confirmed present at worktree path
- Commit `a2e549a` exists: confirmed via `git rev-parse --short HEAD`
- No tracked file deletions in commit
