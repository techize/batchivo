# Phase 2: Consolidated List View - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the existing `/inventory` + `/filaments` dual-route setup with a single `/filaments` route that renders a FilamentType-grouped list. Each row represents a FilamentType (e.g., "JAYO Black PETG × 3") with spool count, labeled count, and sample status badges. Clicking a row opens a read-only Sheet showing the child Spool records. Users can toggle `has_sample` inline on the FilamentType row. A search box + filter sheet allows filtering by brand, color, material type, label status, and sample status.

This phase is full-stack: a new backend aggregation endpoint, new frontend list component, route changes, and sidebar nav update.

</domain>

<decisions>
## Implementation Decisions

### Route & Navigation

- **D-01:** `/filaments` is the canonical route. `/materials` is NOT used — yarn and future material types each have their own feature-specific routes (knitting module already follows this pattern).
- **D-02:** `/inventory` route is kept as a client-side redirect to `/filaments` (not hard-removed). Treat as production-critical — external bookmarks may exist.
- **D-03:** Sidebar nav shows a single "Filaments" entry linking to `/filaments`. The duplicate "Inventory" entry is removed.
- **D-04:** Page heading is **"Filament Library"** — reflects the new two-tier model (browsing types, not a flat spool list).

### List Row Design

- **D-05:** Rows group by FilamentType. Each row shows: brand, color (with swatch dot when `color_hex` is available, else text-only), material type, spool count badge, labeled count badge ("2/3 labeled"), and sample status badge ("Sample ✓" or "Sample ✗").
- **D-06:** Inline `has_sample` toggle lives directly on the FilamentType row — a quick tap marks the sample printed without opening the sheet.
- **D-07:** On mobile (< lg breakpoint), FilamentType rows use the **Card layout** (consistent with existing `SpoolCard.tsx` pattern). On desktop (≥ lg), a table layout.

### Sheet (Spool Drill-Down)

- **D-08:** Clicking a FilamentType row (anywhere except the `has_sample` toggle) opens a **Sheet** (shadcn/ui `Sheet`) listing child Spool records.
- **D-09:** The Sheet is **read-only** — shows spool_id, current weight, is_labeled status, is_active status per spool. No Edit/Delete/Update Weight actions in the sheet. These are deferred to Phase 4 detail pages.
- **D-10:** The Sheet loads spool data via a **separate fetch**: `GET /api/v1/filament-types/{id}/spools` (new endpoint). It does NOT reuse the flat `/api/v1/spools` endpoint.

### Backend API

- **D-11:** A new `GET /api/v1/filament-types` (list) endpoint returns **aggregated rows** with pre-computed counts from the database. Response shape per row: `id`, `brand`, `color`, `color_hex`, `material_type_name`, `material_type_code`, `has_sample`, `spool_count`, `labeled_count`. Full FilamentType detail fields (temps, diameter, finish, etc.) are NOT included in the list response.
- **D-12:** A new `GET /api/v1/filament-types/{id}/spools` endpoint returns the child Spools for a given FilamentType. Used by the Sheet.
- **D-13:** The list endpoint supports filtering by: `brand` (text search), `color` (text search), `material_type_id`, `needs_labels` (boolean: any spool `is_labeled=false`), `needs_sample` (boolean: `has_sample=false`).

### Filter UX

- **D-14:** Filter entry point: **search box + "Filters" button** side by side in the page header. Active filter count badge appears on the Filters button when any filter is active.
- **D-15:** Clicking Filters opens a **Sheet/popover** with all 5 dimensions: brand (text), color (text), material type (select), label status, sample status.
- **D-16 (Claude's Discretion):** Label and sample status filters use **separate independent toggles** ("Needs labels" and "No sample") — the same pattern as the existing "Low Stock Only" button. This matches how the label session workflow will use them: filter to types needing labels, then go label.

### Claude's Discretion

- Color display: use a color swatch dot (filled circle with `color_hex`) when the hex value is available, fall back to text-only. Match whatever pattern already exists in `SpoolCard.tsx` for consistency.
- Label/sample status filter toggles follow the existing "Low Stock Only" button pattern: toggle buttons that become active/filled when selected.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` — NAV-01, NAV-02, LIST-01, LIST-02, LIST-03; canonical source for Phase 2 requirements
- `.planning/PROJECT.md` — Key Decisions table and constraints (no breaking changes, RLS enforcement)

### Existing Frontend Code to Modify/Replace
- `frontend/src/App.tsx` — Route tree; `inventoryRoute` and `filamentsRoute` are defined here; redirect and route changes go here
- `frontend/src/components/inventory/SpoolList.tsx` — The existing flat spool list being replaced; review before building the new list to understand what to preserve
- `frontend/src/components/inventory/SpoolCard.tsx` — Mobile card pattern to reuse for `FilamentTypeCard`
- `frontend/src/components/layout/` — Sidebar nav where the "Inventory" duplicate entry must be removed

### Existing Types & API Clients
- `frontend/src/types/spool.ts` — Existing Spool types; new `FilamentTypeListItem` type needed alongside these
- `frontend/src/lib/api/spools.ts` — Existing spool API client; new `filament-types.ts` API client follows same pattern

### Phase 1 Backend (Canonical Source for Models/Endpoints)
- `backend/app/models/filament_type.py` — FilamentType model created in Phase 1 (read for field names before building API)
- `backend/app/api/v1/filament_types.py` — Phase 1 FilamentType CRUD endpoints (Phase 2 extends with list aggregation and `/spools` sub-resource)
- `backend/app/auth/dependencies.py` — `get_current_tenant`, `CurrentTenant`, `CurrentUser` — required on all new endpoints

### Patterns
- `backend/app/modules/threed_print/spools.py` — Module-level route registration pattern for new FilamentType list endpoints
- `frontend/src/components/ui/` — shadcn/ui Sheet, Badge, Input, Button — used for the sheet, filter UI, and row badges

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SpoolCard.tsx` — Mobile card component; `FilamentTypeCard` should follow the same Card + action layout. Review for color swatch pattern.
- `shadcn/ui Sheet` — Already in the component library; used for the spool drill-down sheet and filter sheet.
- `shadcn/ui Badge` — Already used extensively in `SpoolList.tsx`; reuse for spool count / labeled count / sample status badges.
- `useQuery` from TanStack Query — Established pattern; `useFilamentTypes` hook wraps the new list endpoint, `useFilamentTypeSpools(id)` wraps the sheet endpoint.
- `materialTypesApi.list()` — Already exists in `spools.ts`; reused for the material type filter dropdown.

### Established Patterns
- All frontend API clients live in `frontend/src/lib/api/<resource>.ts` — create `filament-types.ts` following the same structure as `spools.ts`
- All hooks in `frontend/src/hooks/use<Name>.ts` — create `useFilamentTypes.ts`
- All tenant-scoped backend endpoints inject `CurrentTenant` via `Depends(get_current_tenant)` — mandatory on all new endpoints
- Backend SQL aggregation: use SQLAlchemy `func.count()` with `GROUP BY filament_type_id` for spool_count and labeled_count
- Mobile/desktop split: `<div className="lg:hidden">` (cards) + `<div className="hidden lg:block">` (table) — same breakpoint as SpoolList

### Integration Points
- `App.tsx` — Add TanStack Router redirect: `inventoryRoute` redirects to `/filaments` instead of rendering the old component
- Sidebar nav component (in `frontend/src/components/layout/`) — Remove "Inventory" entry, keep "Filaments"
- `backend/app/modules/threed_print/` — Register new FilamentType list + sheet endpoints alongside existing spool routes
- Phase 1's FilamentType CRUD API — Phase 2 adds `?include_counts=true` behavior or a separate aggregated list endpoint on top

</code_context>

<specifics>
## Specific Ideas

- The `/inventory` redirect is production-critical (external bookmarks may exist) — implement as a TanStack Router `redirect` in the route definition, not just a removed route.
- "Filament Library" is the page heading — this is a specific choice, not a convention default.
- The `has_sample` toggle on the row should be visually distinct enough to not accidentally trigger when scrolling (consider a small checkbox or icon button, not a full-row click target).
- Filter sheet and spool detail sheet are two different sheets — make sure they don't conflict in the component tree.

</specifics>

<deferred>
## Deferred Ideas

- `/materials` as a generic route hub for all material types — would require a separate dedicated phase and architectural decision about how knitting, filament, and future types relate in nav
- Per-spool Edit / Delete / Update Weight actions — deferred to Phase 4 (detail pages)
- Color-based grouping within FilamentType rows (e.g., color grid showing all shades of a brand) — out of scope for Phase 2

</deferred>

---

*Phase: 2-Consolidated List View*
*Context gathered: 2026-05-20*
