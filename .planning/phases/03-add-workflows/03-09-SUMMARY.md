---
phase: 03-add-workflows
plan: "09"
subsystem: backend-api, frontend-hooks
tags: [rls, cache-invalidation, bug-fix, multi-tenant, spool-creation]
dependency_graph:
  requires: ["03-03", "03-04"]
  provides: ["spool-create-rls-fix", "spool-create-cache-invalidation"]
  affects: ["filament-library-list", "bulk-add-dialog", "batch-add-dialog"]
tech_stack:
  added: []
  patterns: ["rls-re-establishment-after-rollback", "query-key-prefix-invalidation"]
key_files:
  modified:
    - backend/app/api/v1/filament_types.py
    - frontend/src/hooks/useFilamentTypes.ts
decisions:
  - "Re-execute SET LOCAL inside if settings.rls_enabled guard — consistent with existing RLS toggle pattern in get_tenant_db"
  - "Invalidate filament-type-spools by prefix — clears all per-type spool queries (identified by filamentTypeId suffix)"
  - "No change to the second nested IntegrityError handler in each function — it raises HTTP 409 immediately with no further DB writes"
metrics:
  duration_minutes: 12
  completed_at: "2026-05-27T08:55:15Z"
  tasks_completed: 2
  files_modified: 2
requirements:
  - ADD-02
  - ADD-04
---

# Phase 03 Plan 09: RLS Re-establishment and Cache Invalidation Fix Summary

**One-liner:** Fixed two-part UAT gap: PostgreSQL RLS context re-established after rollback in bulk/batch create retry paths, and filament-type-spools cache invalidated on mutation success.

## What Was Built

### Task 1 — RLS Context Re-establishment (backend/app/api/v1/filament_types.py)

`SET LOCAL app.current_tenant_id` is transaction-scoped in PostgreSQL. When `db.rollback()` is called inside the `except IntegrityError` retry block, the RLS context set by `get_tenant_db` is cleared. Any subsequent INSERT (in `_find_or_create_filament_type` or spool creation) then fails the RLS policy silently, causing the endpoint to return 201 but no data to be written.

Fix applied:
- Added `text` to the `from sqlalchemy import` line
- Added `from app.config import settings` import
- After `await db.rollback()` in `bulk_create`'s IntegrityError handler, re-execute `SET LOCAL app.current_tenant_id = :tenant_id` guarded by `settings.rls_enabled`
- Same fix applied to `batch_create`'s IntegrityError handler

The second nested `except IntegrityError` in each function (which raises HTTP 409) was left unchanged — it performs no further DB writes.

### Task 2 — Cache Invalidation Broadening (frontend/src/hooks/useFilamentTypes.ts)

The `onSuccess` callbacks in `useBulkCreateFilamentType` and `useBatchCreateFilamentTypes` only invalidated `['filament-types']`. The spool drill-down sheet uses a separate query keyed on `['filament-type-spools', filamentTypeId]`. After a successful bulk/batch add, the sheet would show stale (empty) data unless the user navigated away and back.

Fix applied:
- Both mutation `onSuccess` callbacks now call `invalidateQueries` for both `['filament-types']` and `['filament-type-spools']`
- Invalidating the `['filament-type-spools']` prefix clears all per-type spool queries regardless of the filamentTypeId suffix

## Verification Results

- `grep -c "SET LOCAL app.current_tenant_id" backend/app/api/v1/filament_types.py` → 2 (bulk_create + batch_create)
- `grep -c "filament-type-spools" frontend/src/hooks/useFilamentTypes.ts` → 3 (useFilamentTypeSpools definition + 2 mutation onSuccess handlers)
- `poetry run ruff check app/api/v1/filament_types.py` → All checks passed
- `poetry run pytest tests/integration/test_filament_types_api.py -x -q` → 33 passed
- `npx tsc --noEmit --skipLibCheck` → no errors for useFilamentTypes.ts

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | b9e5861 | fix(03-09): re-establish RLS context after rollback in bulk_create and batch_create |
| 2    | 13d126c | fix(03-09): invalidate filament-type-spools cache after bulk and batch create mutations |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no placeholder data or hardcoded stubs in the changed files.

## Threat Flags

No new threat surface introduced. Changes are confined to retry paths of existing authenticated endpoints and client-side cache management.

## Self-Check: PASSED

- `backend/app/api/v1/filament_types.py` exists and contains 2 SET LOCAL occurrences
- `frontend/src/hooks/useFilamentTypes.ts` exists and contains 3 filament-type-spools occurrences
- Commits b9e5861 and 13d126c exist in git log
