---
plan: 03-01
status: complete
wave: 0
phase: 03-add-workflows
subsystem: backend/tests, frontend/tests
tags: [tdd, test-stubs, bulk-create, batch-create]
dependency_graph:
  requires: []
  provides: [test-contract-bulk-create, test-contract-batch-create, test-contract-add-filament-dialog]
  affects: [03-02, 03-03, 03-04]
tech_stack:
  added: []
  patterns: [xfail stubs, it.todo stubs]
key_files:
  created:
    - frontend/src/components/filaments/AddFilamentDialog.test.tsx
  modified:
    - backend/tests/integration/test_filament_types_api.py
decisions:
  - Used xfail(strict=False) for backend stubs so collection passes even when endpoints don't exist
  - Used it.todo for frontend stubs since component doesn't exist yet
metrics:
  duration: ~5 minutes
  completed: 2026-05-20
---

## What Was Done

- Appended TestBulkCreate (8 methods) and TestBatchCreate (6 methods) as xfail stubs to `backend/tests/integration/test_filament_types_api.py`
- Added `import re` at top of integration test file (required by spool_id_format test)
- Added `_bulk_payload` and `_batch_payload` module-level helpers after the existing `_valid_payload` helper
- Created `frontend/src/components/filaments/AddFilamentDialog.test.tsx` with 11 `it.todo` stubs

## Verification

- Both new test classes collected without import errors: 14 tests total (8 + 6)
- All new tests xfail (not error) — endpoints not yet implemented
- Existing test collection unaffected (pre-existing DB connection failure is an environment issue, not caused by these changes)
- AddFilamentDialog.test.tsx has 11 it.todo entries
- Acceptance criteria: `grep -E "TestBulkCreate|TestBatchCreate"` lists 14 items

## Commit

- 27789ba: test(03-01): add failing test stubs for bulk-create and batch-create workflows

## Deviations from Plan

None - plan executed exactly as written.
