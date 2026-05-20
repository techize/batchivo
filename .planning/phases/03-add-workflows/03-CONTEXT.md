# Phase 3: Add Workflows - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two filament addition workflows to the FilamentLibrary page:

1. **Bulk add** — User creates a new FilamentType (brand + color + material type + optional fields) and sets a quantity (1–20); the backend auto-generates that many Spool records with sequential FIL-NNN IDs in a single atomic transaction. All spools land in the list as "needs label".

2. **Rapid batch add** — User sets a shared weight once, then builds a table of color variants (each row: all FilamentType fields pre-filled from the previous row, user changes whatever differs). One final submit creates all FilamentTypes + one Spool each in a single atomic transaction.

Both workflows surface via a single "+ Add" button in the FilamentLibrary page header, which opens a Dialog with a mode selector.

</domain>

<decisions>
## Implementation Decisions

### Entry Point & Container

- **D-01:** The "+ Add" button lives in the FilamentLibrary page header, beside the existing Filters button (layout: `[Search] [Filters] [+ Add]`).
- **D-02:** Clicking "+ Add" opens a **shadcn/ui Dialog** (not a Sheet — Dialogs signal action, Sheets signal browse). The Dialog is fixed `max-w-lg` with scrollable content. No size transition between mode selector and form.
- **D-03:** The first screen inside the Dialog is a **mode selector**: "Add a batch of identical spools" vs "Add multiple color variants". User always consciously selects which path they're on.
- **D-04:** After a **bulk add** succeeds, the Dialog closes and the FilamentLibrary list refreshes (new types/spools appear with "needs label" badges).
- **D-05:** After a **rapid batch** final submit succeeds, the Dialog stays open. The table clears and the form resets so the user can immediately start another batch.

### Bulk Add Form

- **D-06:** The bulk add form is a **single scrollable form** — no wizard steps. All fields are visible at once.
- **D-07:** Visible fields: brand (required), color (required), material type (required), finish (optional), notes (optional) + a collapsible "More options" section containing color_hex, diameter, extruder_temp, bed_temp, density, pattern, translucent, glow, spool_type.
- **D-08:** Quantity field: numeric input with +/− buttons, range **1–20**. Minimum 1 (quantity = 0 is not allowed — the bulk add workflow requires at least one physical spool).
- **D-09:** Weight per spool: single numeric input field (default **1000g**), applies uniformly to all auto-generated spools.

### Rapid Batch Add Form

- **D-10:** The rapid batch Dialog shows a **weight field at the top** (default 1000g, applies to every spool in the batch), then an entry form below it.
- **D-11:** Each color step shows **all FilamentType fields** pre-filled from the previous entry. User changes whatever differs. Color is the only semantically required field per step, but no other field is removed.
- **D-12:** Each step creates **1 spool** (no per-step quantity field). To add 3x of the same color, add it 3 times.
- **D-13:** The form **accumulates entries** — clicking "Add color" appends a row to a **table below the form** (columns: brand, color, material type, finish, with a remove button per row). Nothing is sent to the backend until the user clicks "Submit all".
- **D-14:** After "Submit all" succeeds, the Dialog stays open: the table clears and the form resets to the last-used values for another round.

### Backend API Design

- **D-15:** Two new backend endpoints:
  - `POST /api/v1/filament-types/bulk-create` — accepts `{brand, color, material_type_id, finish, pattern, color_hex, diameter, extruder_temp, bed_temp, density, notes, translucent, glow, spool_type, quantity, initial_weight}`. Backend creates the FilamentType + N Spools atomically. Returns the created FilamentType + list of created Spool IDs.
  - `POST /api/v1/filament-types/batch-create` — accepts `{entries: [{brand, color, material_type_id, finish, pattern, ...}], initial_weight}`. Backend creates all FilamentTypes + one Spool each atomically. Returns list of created FilamentType + Spool pairs.
- **D-16:** Both endpoints generate spool IDs **atomically** server-side: query `MAX(spool_id LIKE 'FIL-%')` within the same transaction, reserve the full range, create all spools. No sequential round-trips.
- **D-17:** spool_id format is always `FIL-NNN` (zero-padded 3+ digits, e.g., FIL-001, FIL-042). No configurable prefix in this phase.
- **D-18:** Collision handling: a `UNIQUE` constraint exists on `(tenant_id, spool_id)`. If a collision occurs (race condition), the backend retries once with the next available ID. After one retry failure, return HTTP 409.

### Claude's Discretion

- Material type field in the add forms: use a `Select` dropdown populated from the existing `materialTypesApi.list()` endpoint (same pattern as the filter sheet in Phase 2).
- Error display within the Dialog: use shadcn/ui `Alert` with `AlertDescription` for API errors (same pattern as `CreateRunWizard`).
- The mode selector screen layout: two large clickable cards describing each mode — reuse the Card component already in the project.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` — ADD-01, ADD-02, ADD-03, ADD-04, ADD-05 (Phase 3 requirements)
- `.planning/PROJECT.md` — Key Decisions table and constraints (RLS enforcement, no breaking changes, migration safety)

### Phase 2 Output (Base to Extend)
- `frontend/src/pages/FilamentLibrary.tsx` — The page receiving the "+ Add" button; read header layout before adding
- `frontend/src/components/filaments/FilamentTypeFilterSheet.tsx` — Filter sheet pattern (shadcn Sheet + form fields) — reference for how the separate filter/dialog sheets coexist
- `frontend/src/hooks/useFilamentTypes.ts` — TanStack Query hooks; bulk/batch mutations follow same pattern

### Backend APIs to Create
- `backend/app/api/v1/filament_types.py` — Existing FilamentType endpoints; new bulk-create and batch-create go here
- `backend/app/api/v1/spools.py` — Spool duplicate endpoint (lines ~370–430) — contains the `FIL-NNN` auto-increment logic to reuse in bulk create
- `backend/app/models/spool.py` — Spool model (spool_id field, initial_weight constraint)
- `backend/app/models/filament_type.py` — FilamentType model (all fields being created)
- `backend/app/auth/dependencies.py` — `CurrentTenant`, `CurrentUser`, `TenantDB` — required on all new endpoints

### Existing Patterns to Follow
- `frontend/src/components/production-runs/CreateRunWizard.tsx` — Multi-step Dialog/wizard with table accumulation and submit; reference for how to manage accumulated rows state and error display
- `frontend/src/lib/api/spools.ts` — API client module pattern; new `filament-types.ts` methods follow this
- `frontend/src/components/ui/` — shadcn/ui Dialog, Table, Alert, Input, Select, Button, Badge — all available

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `shadcn/ui Dialog` — Available in the component library; unused for add flows so far. Import from `@/components/ui/dialog`.
- `materialTypesApi.list()` — Already called in the filter sheet; reuse for the material type Select in the add forms.
- `useFilamentTypes` hook + `refetch` — After bulk/batch submit, call `refetch()` (or invalidate the query key) to refresh the library list.
- `FIL-NNN auto-increment logic` — Already implemented in `duplicate_spool` (backend/app/api/v1/spools.py ~L400). Extract to a shared helper and reuse in the two new endpoints.
- `CreateRunWizard.tsx` — Table accumulation pattern (rows state, remove handler, submit-all with `useMutation`). Reference architecture for the rapid batch accumulator.

### Established Patterns
- All API clients in `frontend/src/lib/api/<resource>.ts` — Add `bulkCreate` and `batchCreate` methods to `filament-types.ts`.
- All hooks in `frontend/src/hooks/use<Name>.ts` — Add `useBulkCreateFilamentType` and `useBatchCreateFilamentTypes` mutation hooks.
- All tenant-scoped backend endpoints inject `CurrentTenant` via `Depends(get_current_tenant)` — mandatory.
- Multi-tenant atomic inserts: create all records in one `async with db.begin():` block; roll back all on failure.

### Integration Points
- `FilamentLibrary.tsx` — Add `useState` for Dialog open state; pass `onSuccess` callback to invalidate the `useFilamentTypes` query.
- `backend/app/modules/threed_print/` — Register new bulk-create and batch-create router entries alongside existing FilamentType routes.
- Existing `FilamentTypeAggregatedListResponse` schema — After bulk/batch add, the list endpoint returns updated aggregated rows with the new types included.

</code_context>

<specifics>
## Specific Ideas

- Mode selector first screen: two large Cards (shadcn/ui Card) inside the Dialog — one for "Batch of identical spools", one for "Color variants". Visual split makes the mental model immediately clear.
- The "+ Add" button in the FilamentLibrary header should be visually distinct from the Filters button — use the primary Button variant (filled) vs. the outline variant on Filters.
- For the rapid batch table, show a color swatch dot (if color_hex is available) alongside the color name in each row — consistent with the FilamentTypeRow/FilamentTypeCard pattern from Phase 2.
- The bulk add "More options" section should use a shadcn/ui Collapsible or an accordion-style toggle. Keep it collapsed by default so the happy path (brand + color + type + quantity) is clean.

</specifics>

<deferred>
## Deferred Ideas

- Configurable spool_id prefix per tenant (e.g., PLA-001 instead of FIL-001) — YAGNI; revisit if the need arises
- FilamentType creation without any spools (quantity = 0) — not in scope for this phase; create a type-only management flow separately if needed
- Mixed spool weights per rapid batch entry — deferred; single weight covers the common case

</deferred>

---

*Phase: 3-Add Workflows*
*Context gathered: 2026-05-20*
