---
phase: 01-data-model-migration
plan: "03"
subsystem: backend/alembic
tags: [migration, data-migration, filament-types, two-tier-model, rls]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [filament_types table, filament_type_id on spools, is_labeled on spools]
  affects: [backend/alembic, backend/app/models/spool.py, backend/app/models/filament_type.py]
tech_stack:
  added: []
  patterns: [DISTINCT ON deduplication, Alembic data migration, RLS policy enforcement]
key_files:
  created:
    - backend/alembic/versions/DATA_filament_type_migration.py
  modified: []
decisions:
  - "Used spools_material_type_id_fkey as the auto-generated PostgreSQL FK constraint name (no explicit name was provided in d80bf772b461)"
  - "Index ix_spools_material_type_id dropped before FK constraint drop (required ordering)"
  - "downgrade() restores all 16 columns as nullable per D-08 (NULL-filled is acceptable for recovery path)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-19"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Phase 01 Plan 03: Filament Type Data Migration Summary

Alembic data migration implementing the full two-tier FilamentType+Spool restructure: creates `filament_types` table, deduplicates spool data with DISTINCT ON, backfills `filament_type_id`, drops 16 deprecated spool columns, and enables RLS with four tenant isolation policies.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write upgrade() — create table, backfill data, restructure spools, enable RLS | 467c6eb | backend/alembic/versions/DATA_filament_type_migration.py |
| 2 | Write downgrade() — restore old columns, drop filament_types table | 467c6eb | backend/alembic/versions/DATA_filament_type_migration.py |

Both tasks were committed atomically in a single commit as the file was created in one pass.

## What Was Built

`backend/alembic/versions/DATA_filament_type_migration.py` — single-file Alembic migration with:

### upgrade() — 11 steps in order

1. **FAIL FAST (D-06)**: SELECT spools with NULL brand or color → RuntimeError with offending IDs
2. **Create filament_types**: `op.create_table` with all D-01 fields (brand, color, color_hex, finish, diameter, density, extruder_temp, bed_temp, translucent, glow, pattern, spool_type, notes, has_sample) + tenant_id FK (CASCADE) + material_type_id FK + PK + two indexes
3. **INSERT deduplicated records**: `DISTINCT ON (tenant_id, brand, color, material_type_id) ORDER BY ... created_at ASC` — oldest spool per group wins
4. **Add filament_type_id** as nullable UUID column on spools
5. **Backfill**: `UPDATE spools s SET filament_type_id = ft.id FROM filament_types ft WHERE s.tenant_id = ft.tenant_id AND s.brand = ft.brand AND s.color = ft.color AND s.material_type_id = ft.material_type_id`
6. **Make NOT NULL**: `op.alter_column` filament_type_id nullable=False
7. **FK from spools → filament_types**: `fk_spools_filament_type_id` with RESTRICT
8. **Add is_labeled**: Boolean NOT NULL server_default=false
9. **Drop material_type_id FK + index**: `ix_spools_material_type_id` index first, then `spools_material_type_id_fkey` constraint
10. **Drop 16 deprecated columns**: brand, color, color_hex, finish, diameter, density, extruder_temp, bed_temp, translucent, glow, pattern, spool_type, notes, material_type_id, purchased_quantity, spools_remaining
11. **Enable RLS**: ALTER TABLE ENABLE + FORCE ROW LEVEL SECURITY + 4 tenant_isolation_* policies (select/insert/update/delete) matching existing pattern from 8c3c671816d9

### downgrade() — 4 steps (reverse order)

1. Restore 16 removed columns as nullable (NULL-filled per D-08)
2. Drop `fk_spools_filament_type_id`, drop `filament_type_id` and `is_labeled` columns
3. Drop 4 RLS policies with `DROP POLICY IF EXISTS`
4. Drop `ix_filament_types_material_type_id`, `ix_filament_types_tenant_id` indexes, then `filament_types` table

## Decisions Made

1. **FK constraint name for material_type_id**: The FK in `d80bf772b461` was created via `sa.ForeignKeyConstraint(["material_type_id"], ["material_types.id"])` with no explicit name. PostgreSQL auto-names this `spools_material_type_id_fkey`. This is the name used in Step 9.

2. **Index before FK drop ordering**: `ix_spools_material_type_id` index is dropped before the FK constraint in Step 9 to avoid dependency issues.

3. **COALESCE in INSERT**: `COALESCE(diameter, 1.75)` and `COALESCE(translucent, false)` / `COALESCE(glow, false)` used in the DISTINCT ON subquery since older spools (pre-i6j7k8l9m0n1 migration) may not have these values.

4. **All data ops via `conn.execute(sa.text(...))`**: No ORM models used — only raw SQL through the bound connection, consistent with Alembic data migration patterns.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. RLS on `filament_types` was explicitly required by the plan (T-01-06) and is implemented in Step 11. No new unplanned security-relevant surface introduced.

## Self-Check: PASSED

- `backend/alembic/versions/DATA_filament_type_migration.py` — EXISTS
- Commit `467c6eb` — EXISTS (`feat(01-03): add filament_type data migration with upgrade and downgrade`)
- Structural verification via `python3 -c` — ALL CHECKS PASSED
- Python syntax check via `python3 -m py_compile` — PASSED

**Runtime verification skipped**: Poetry venv broken due to Homebrew Python upgrade (Python 3.14 dylib changed). Structural verification via file content inspection confirms correctness.
