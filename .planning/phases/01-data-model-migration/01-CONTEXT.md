# Phase 1: Data Model Migration - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the FilamentType model (brand, color, material_type_id, diameter, finish, pattern, temperatures, density, has_sample, color_hex, translucent, glow, spool_type, notes) and update the Spool model to reference it. Write a single Alembic migration that infers FilamentType records from existing Spool data and migrates all existing spools to the two-tier structure, removing deprecated fields purchased_quantity and spools_remaining. Add is_labeled to Spool.

This phase is backend-only: models, schemas, migration, and updated API endpoints. No frontend changes.

</domain>

<decisions>
## Implementation Decisions

### Field Split — FilamentType vs. Spool

- **D-01:** The following fields move from Spool to FilamentType: `brand`, `color`, `color_hex`, `finish`, `pattern`, `spool_type`, `translucent`, `glow`, `diameter`, `density`, `extruder_temp`, `bed_temp`, `notes`, `has_sample` (new).
- **D-02:** The following fields stay on Spool (per-unit): `spool_id`, `initial_weight`, `current_weight`, `empty_spool_weight`, `storage_location`, `qr_code_id`, `is_active`, `is_labeled` (new), `purchase_price`, `supplier`, `purchase_date`.
- **D-03:** `material_type_id` FK stays on FilamentType (it was on Spool; it moves up to the type level). Spool references FilamentType via a new `filament_type_id` FK.

### Deduplication Key for Migration

- **D-04:** Two existing Spool records are considered the same FilamentType when `brand + color + material_type_id` match (case-sensitive, NULL treated as non-matching). Diameter is NOT part of the uniqueness key — diameter differences do not create separate FilamentType records.
- **D-05:** When multiple spools map to the same FilamentType, the values from the **oldest spool by created_at** populate the FilamentType's shared fields (color_hex, density, temps, finish, pattern, etc.).
- **D-06:** If any existing Spool has NULL brand or NULL color, the migration must **fail fast** with a clear error listing the affected spool IDs. Do not proceed with NULL brand/color data — require the user to fix it before running the migration.

### Deprecated Field Removal

- **D-07:** `purchased_quantity` and `spools_remaining` are removed from the Spool table in Phase 1's migration (same migration that creates FilamentType). Clean break — no staged removal.
- **D-08:** The migration MUST include a `downgrade()` path: restores `purchased_quantity` and `spools_remaining` columns (NULL-filled), drops FilamentType table, and restores `brand`, `color`, etc. on Spool. Full reversibility required.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Model & Requirements
- `.planning/REQUIREMENTS.md` — v1 requirements DATA-01 through DATA-05; canonical source for what Phase 1 must deliver
- `.planning/PROJECT.md` — Key Decisions table and constraint list (migration safety, RLS enforcement, no breaking changes)

### Existing Model to Migrate
- `backend/app/models/spool.py` — Current Spool model; all fields being split/removed are defined here
- `backend/app/models/material_type.py` — MaterialType model that FilamentType will reference via FK
- `backend/app/schemas/spool.py` — Existing Pydantic schemas; will need SpoolResponse updated to nest FilamentType

### Migration Infrastructure
- `backend/alembic/env.py` — Alembic environment; RLS integration and migration runner setup
- `backend/alembic/versions/` — ~90 existing migrations; read 2–3 recent ones for naming and pattern conventions

### API Routes to Update
- `backend/app/modules/threed_print/spools.py` — Module-level route registration for spools
- `backend/app/api/v1/spools.py` (if exists) — Spool CRUD endpoints that will need FilamentType awareness

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Base, UUIDMixin, TimestampMixin` from `backend/app/models/base.py` — FilamentType model inherits these exactly like all other models
- Existing `MaterialType` model — FilamentType adds a FK to this; no changes to MaterialType needed

### Established Patterns
- All tenant-scoped models carry `tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)` — FilamentType must follow this exactly
- Eager loading with `lazy="joined"` on FK relationships (e.g., Spool's current `material_type` relationship) — FilamentType's `material_type` and Spool's `filament_type` relationships should use the same pattern
- Pydantic schemas follow Base/Create/Update/Response hierarchy — FilamentType needs all four; SpoolResponse needs to nest `FilamentTypeResponse`
- Alembic migrations use autogenerate then manual review; data backfill logic (the FilamentType inference) must be hand-written in the migration's `upgrade()` body

### Integration Points
- `backend/app/modules/threed_print/` — Spool routes registered here; FilamentType routes will register in the same module
- `backend/app/auth/dependencies.py` — `get_tenant_db` dependency sets RLS context; all FilamentType endpoints must use this, not `get_db`
- `backend/app/api/v1/spools.py` — Existing Spool endpoints will need `filament_type_id` added to create/update schemas; `brand`, `color`, etc. removed from direct Spool payloads

</code_context>

<specifics>
## Specific Ideas

- Migration fail-fast on NULL brand/color: surface a clean list of spool IDs with missing data before attempting any table creation — do this as the first step in `upgrade()` so it's easy to fix and retry
- Deduplication uses `brand + color + material_type_id` (not diameter) — this may produce FilamentType records with `diameter = NULL` if spools in the same group have different diameters; the migration should pick the oldest spool's diameter value (per D-05) rather than leaving it NULL

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Data Model Migration*
*Context gathered: 2026-05-19*
