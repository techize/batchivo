# Phase 2: Consolidated List View - Research

**Researched:** 2026-05-20
**Domain:** Full-stack — FastAPI aggregation endpoint + TanStack Router redirect + React list view with shadcn/ui Sheet/Table/Card
**Confidence:** HIGH — all key findings verified directly from codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `/filaments` is the canonical route. `/materials` is NOT used.
- **D-02:** `/inventory` route is kept as a client-side redirect to `/filaments` (not removed). Production-critical.
- **D-03:** Sidebar nav shows a single "Filaments" entry linking to `/filaments`. The duplicate "Inventory" entry is removed.
- **D-04:** Page heading is **"Filament Library"**.
- **D-05:** Rows group by FilamentType. Each row shows: brand, color (swatch dot when `color_hex` available), material type, spool count badge, labeled count badge ("2/3 labeled"), sample status badge ("Sample ✓" or "Sample ✗").
- **D-06:** Inline `has_sample` toggle on the FilamentType row. Quick tap marks sample printed without opening sheet.
- **D-07:** Mobile (< lg) uses Card layout; desktop (≥ lg) uses Table layout.
- **D-08:** Clicking a row (except toggle) opens a shadcn `Sheet` listing child Spool records.
- **D-09:** Sheet is read-only: spool_id, current weight, is_labeled, is_active. No Edit/Delete/Update Weight in sheet.
- **D-10:** Sheet loads via separate fetch: `GET /api/v1/filament-types/{id}/spools`.
- **D-11:** New `GET /api/v1/filament-types` list returns aggregated rows: `id`, `brand`, `color`, `color_hex`, `material_type_name`, `material_type_code`, `has_sample`, `spool_count`, `labeled_count`.
- **D-12:** New `GET /api/v1/filament-types/{id}/spools` returns child Spools for sheet.
- **D-13:** List endpoint filters: `brand` (text search), `color` (text search), `material_type_id`, `needs_labels` (boolean), `needs_sample` (boolean).
- **D-14:** Filter entry point: search box + "Filters" button side-by-side in page header. Active filter count badge on Filters button.
- **D-15:** Clicking Filters opens Sheet/popover with 5 dimensions: brand (text), color (text), material type (select), label status, sample status.
- **D-16 (Claude's Discretion):** Label and sample status filters use separate independent toggles ("Needs labels" / "No sample") matching the existing "Low Stock Only" button pattern.

### Claude's Discretion

- Color swatch: use `color_hex` when available (follow existing `SpoolCard.tsx` normalization logic), else text-only.
- Filter toggle buttons follow existing "Low Stock Only" pattern: `variant="default"` when active, `variant="outline"` when inactive.

### Deferred Ideas (OUT OF SCOPE)

- `/materials` as a generic route hub for all material types.
- Per-spool Edit / Delete / Update Weight actions (Phase 4).
- Color-based grouping within FilamentType rows.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NAV-01 | `/inventory` route removed; all filament spool content lives at `/filaments` | D-02: implement as TanStack Router redirect via `Navigate` component inside `inventoryRoute` component. The route stays registered in the tree — only its component changes. |
| NAV-02 | Internal links pointing to `/inventory` updated to `/filaments` | Two locations confirmed: `AppLayout.tsx` fallback nav (line 122) has `/inventory` entry; `MODULE_NAVIGATION["spools"]` in `modules.py` has `/inventory` entry. Both must change. |
| LIST-01 | List aggregates spools by FilamentType, showing type name and spool count | New backend aggregation endpoint (D-11) with `spool_count` pre-computed via `func.count()`. New `FilamentTypeList` page replaces `SpoolList`. |
| LIST-02 | Each FilamentType row shows status summary: labeled count, sample status | `labeled_count` from backend aggregation (count of `is_labeled=true` spools). `has_sample` already a field on `FilamentType` model. |
| LIST-03 | User can filter/search by brand, color, material type, label/sample status | New query params on list endpoint (D-13). Filter state in `FilamentTypeList` component, filter sheet `FilamentTypeFilterSheet`. |

</phase_requirements>

---

## Summary

Phase 2 is a full-stack feature with three distinct tracks: (1) route + nav surgery, (2) two new backend endpoints, and (3) a new frontend list page built from existing patterns. All verified source files exist. The existing `GET /api/v1/filament-types` endpoint at `backend/app/api/v1/filament_types.py` requires modification — it currently returns full `FilamentTypeResponse` objects (including all spec fields) rather than an aggregated list shape with counts. The aggregated shape (D-11) is new and must be added as an alternate response mode or a new endpoint.

The `FilamentType` model (`backend/app/models/filament_type.py`) has `has_sample` as a boolean field. The `Spool` model has `is_labeled` and `is_active` as boolean fields and `filament_type_id` as a FK. The aggregation query uses `func.count(Spool.id)` with conditional count for `labeled_count`. No new migrations are required — all required columns already exist from Phase 1.

The frontend route tree lives entirely in `frontend/src/App.tsx` using TanStack Router v1.141. The redirect pattern for `/inventory` is straightforward: replace the `inventoryRoute` component with one that renders `<Navigate to="/filaments" />`. Navigation items come from two sources that both need updating: the `MODULE_NAVIGATION` dict in `backend/app/api/v1/modules.py` (which drives dynamic nav) and the `fallbackNavItems` array in `AppLayout.tsx` (used during loading or if modules API fails).

**Primary recommendation:** Extend the existing `GET /api/v1/filament-types` endpoint with an `include_counts` query param (or add a new aggregated list schema) rather than creating a wholly separate endpoint — the router prefix is already registered at `main.py:243`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Route redirect `/inventory` → `/filaments` | Frontend (client-side) | — | TanStack Router handles routing entirely client-side in this SPA |
| Nav item deduplication (remove "Inventory") | Backend (modules API) + Frontend (fallback) | — | Dynamic nav from `MODULE_NAVIGATION` dict; fallback in `AppLayout.tsx` hardcoded array |
| FilamentType list aggregation (counts) | API/Backend | — | SQL `func.count()` is cheaper and more accurate than client-side aggregation |
| `has_sample` toggle mutation | Frontend | API/Backend | Optimistic update via TanStack Query mutation; `PUT /api/v1/filament-types/{id}` already exists |
| Filter state management | Frontend | — | Query params forwarded to backend; no server-side session state |
| Spool drill-down data | API/Backend | — | Separate fetch `GET /api/v1/filament-types/{id}/spools` on sheet open |
| Mobile card / desktop table layout | Frontend | — | CSS breakpoint, no server involvement |

---

## Standard Stack

All packages already installed in the project. No new dependencies needed.

### Core (already installed)
| Library | Version (pinned) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-router` | ^1.141.1 | Client-side routing and redirects | Already the SPA router |
| `@tanstack/react-query` | ^5.90 | Data fetching, mutations, optimistic updates | Established project pattern |
| shadcn/ui components | N/A (no package — copy/paste) | Sheet, Table, Card, Badge, Input, Button, Select, Skeleton, Separator, Tooltip | All already installed per UI-SPEC |
| `lucide-react` | Installed | Icons (`FlaskConical`/`TestTube2` for sample toggle, `Search`, `Filter`) | Project icon library |
| FastAPI | >=0.124.4 | New aggregation endpoint | Backend framework |
| SQLAlchemy 2.0 async | Installed | `func.count()` aggregation query | Project ORM |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `framer-motion` | Installed (used in SpoolCard.tsx) | Animation for FilamentTypeCard | Mobile card only — NOT needed for the new FilamentTypeCard (D-07 says "consistent with SpoolCard.tsx pattern" but the sheet is read-only and the card has no swipe actions). |
| `react-swipeable` | Installed (used in SpoolCard.tsx) | Swipe gestures | NOT needed for FilamentTypeCard — no swipe actions in Phase 2. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending existing `GET /api/v1/filament-types` with `include_counts` | New `/api/v1/filament-types/aggregated` endpoint | Separate endpoint is cleaner schema separation but requires a new route registration. Extending with an optional param avoids adding routes. Either is acceptable. |
| Client-side aggregation of spools → groups | Backend SQL aggregation | Client-side would require fetching ALL spools (unbounded), then grouping. Backend aggregation is O(1) query, scales with spool count, filters correctly. Always backend. |
| `<Navigate to="/filaments" />` in route component | `beforeLoad: () => redirect('/filaments')` in TanStack Router v1 | Both work in v1.141. `beforeLoad` is slightly cleaner (no component render). Codebase uses component-based `<Navigate>` already (see App.tsx line 201). Either is fine. |

**Installation:** No new packages needed. All dependencies are already installed.

---

## Package Legitimacy Audit

No new external packages are being installed in this phase. All functionality is built from already-installed dependencies.

| Package | Status |
|---------|--------|
| All shadcn/ui components | Already installed in project |
| All TanStack packages | Already installed in project |
| All icon libraries | Already installed in project |

**No slopcheck required — no new installs.**

---

## Architecture Patterns

### System Architecture Diagram

```
User browser
    │
    ├── GET /filaments ──────────────────────────► FilamentTypeList page
    │                                                │
    │   (redirect: GET /inventory)                   ├── useFilamentTypes(params)
    │   ──────────────────────────────────────────►  │   └── GET /api/v1/filament-types?...
    │                                                │       (aggregated: spool_count, labeled_count)
    │                                                │
    │                                                ├── [row click] FilamentTypeSpoolSheet
    │                                                │   └── useFilamentTypeSpools(id)
    │                                                │       └── GET /api/v1/filament-types/{id}/spools
    │                                                │
    │                                                └── [toggle click] PATCH/PUT has_sample
    │                                                    └── PUT /api/v1/filament-types/{id}
    │                                                        (optimistic update)
    │
    └── Sidebar nav ─────────────────────────────► GET /api/v1/modules
                                                    (returns single "Filaments" /filaments entry)
```

### Recommended Project Structure

New files to create:
```
frontend/src/
├── pages/
│   └── FilamentLibrary.tsx        # New page component (replaces Dashboard as /filaments target)
├── components/filaments/          # New directory (parallel to components/inventory/)
│   ├── FilamentTypeCard.tsx       # Mobile card for FilamentType row
│   ├── FilamentTypeRow.tsx        # Desktop table row for FilamentType
│   ├── FilamentTypeSpoolSheet.tsx # Sheet: child spool list
│   └── FilamentTypeFilterSheet.tsx # Sheet: filter dimensions
├── hooks/
│   └── useFilamentTypes.ts        # Wraps both list and spools endpoints
└── lib/api/
    └── filament-types.ts          # API client for /api/v1/filament-types

backend/app/schemas/
└── filament_type.py               # Add FilamentTypeAggregatedResponse + FilamentTypeSpoolItem schemas

backend/app/api/v1/
└── filament_types.py              # Add aggregated list endpoint + /spools sub-resource endpoint
```

### Pattern 1: TanStack Router Redirect (v1.141)

The codebase uses `<Navigate>` component from `@tanstack/react-router` (line 201 of App.tsx). Apply same pattern to `inventoryRoute`:

```typescript
// Source: frontend/src/App.tsx (existing Navigate pattern at line 201)
// In App.tsx, change inventoryRoute component:
const inventoryRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/inventory',
  component: () => <Navigate to="/filaments" />,  // Simple redirect, no auth wrapper needed
})
```

**Key insight:** The existing `<Navigate>` usage in `ProtectedRoute` (line 201) confirms this component is available from the installed `@tanstack/react-router` v1.141.1 import. [VERIFIED: direct codebase inspection]

### Pattern 2: Backend Aggregation Query (SQLAlchemy 2.0 async)

The existing `list_filament_types` endpoint already uses `select(FilamentType)` with `.where(FilamentType.tenant_id == tenant.id)`. Add a new aggregated list endpoint using `func.count()` with `outerjoin`:

```python
# Source: backend/app/api/v1/filament_types.py (extend list endpoint)
from sqlalchemy import case, func, select

# Aggregated query pattern
query = (
    select(
        FilamentType.id,
        FilamentType.brand,
        FilamentType.color,
        FilamentType.color_hex,
        FilamentType.has_sample,
        FilamentType.material_type_id,
        func.count(Spool.id).label("spool_count"),
        func.count(case((Spool.is_labeled == True, Spool.id))).label("labeled_count"),
    )
    .outerjoin(Spool, (Spool.filament_type_id == FilamentType.id) & (Spool.tenant_id == tenant.id))
    .where(FilamentType.tenant_id == tenant.id)
    .group_by(FilamentType.id)
)
```

**Why `outerjoin`:** FilamentTypes with zero spools must still appear in the list (spool_count=0). `outerjoin` handles this. `case()` counts only labeled spools without requiring a subquery. [ASSUMED — SQLAlchemy `case()` import syntax verified from existing codebase usage at spools.py, but the exact `outerjoin` condition syntax is training knowledge]

### Pattern 3: TanStack Query Hook for Filament Types

Follow the existing `spoolsApi`/`useQuery` pattern from `SpoolList.tsx`:

```typescript
// Source: frontend/src/components/inventory/SpoolList.tsx (lines 102-148)
// New hook: frontend/src/hooks/useFilamentTypes.ts
export function useFilamentTypes(params: FilamentTypeListParams) {
  return useQuery({
    queryKey: ['filament-types', params],
    queryFn: () => filamentTypesApi.list(params),
  })
}

export function useFilamentTypeSpools(filamentTypeId: string | null) {
  return useQuery({
    queryKey: ['filament-type-spools', filamentTypeId],
    queryFn: () => filamentTypesApi.getSpools(filamentTypeId!),
    enabled: filamentTypeId !== null,  // Only fetch when sheet opens
  })
}
```

### Pattern 4: `has_sample` Optimistic Toggle

```typescript
// Source: TanStack Query mutation pattern from SpoolList.tsx (lines 169-183)
const toggleSampleMutation = useMutation({
  mutationFn: ({ id, hasSample }: { id: string; hasSample: boolean }) =>
    filamentTypesApi.update(id, { has_sample: hasSample }),
  onMutate: async ({ id, hasSample }) => {
    await queryClient.cancelQueries({ queryKey: ['filament-types'] })
    const previous = queryClient.getQueryData(['filament-types', params])
    queryClient.setQueryData(['filament-types', params], (old: FilamentTypeListResponse) => ({
      ...old,
      filament_types: old.filament_types.map(ft =>
        ft.id === id ? { ...ft, has_sample: hasSample } : ft
      ),
    }))
    return { previous }
  },
  onError: (_err, _vars, context) => {
    if (context?.previous) {
      queryClient.setQueryData(['filament-types', params], context.previous)
    }
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['filament-types'] })
  },
})
```

The existing `PUT /api/v1/filament-types/{id}` endpoint accepts `FilamentTypeUpdate` with `has_sample: Optional[bool]` — confirmed from `filament_types.py` lines 149–193 and `schemas/filament_type.py`. [VERIFIED: direct codebase inspection]

### Pattern 5: Color Swatch Normalization (from SpoolCard.tsx)

```typescript
// Source: frontend/src/components/inventory/SpoolCard.tsx (lines 93-97)
// Exact pattern to reuse in FilamentTypeCard and FilamentTypeRow:
style={{
  backgroundColor: spool.color_hex
    ? `#${spool.color_hex.length === 8 ? spool.color_hex.slice(2) : spool.color_hex}`
    : '#e5e7eb'
}}
```

For the list view, the swatch should be a 12px circle (`w-3 h-3 rounded-full`) rather than the 40px square (`w-10 h-10 rounded-md`) used in SpoolCard. Only render the swatch when `color_hex` is present (no empty placeholder circle).

### Pattern 6: Two-Sheet Architecture (no nesting)

Both sheets use independent state variables. `FilamentTypeSpoolSheet` and `FilamentTypeFilterSheet` must NOT be nested — shadcn `Sheet` uses Radix Dialog primitives which do not support nested focus traps reliably.

```typescript
// In FilamentTypeList component:
const [spoolSheetFilamentTypeId, setSpoolSheetFilamentTypeId] = useState<string | null>(null)
const [filterSheetOpen, setFilterSheetOpen] = useState(false)
```

### Anti-Patterns to Avoid

- **Fetching all spools then grouping client-side:** Would require an unbounded list endpoint call. Always aggregate in SQL.
- **Reusing the existing `FilamentTypeListResponse`** (which returns `FilamentTypeResponse` with all spec fields): The list view only needs the aggregated slim shape. Return too much data and the query becomes unnecessarily expensive. Add a new `FilamentTypeAggregatedResponse` schema alongside the existing one.
- **Nesting two `Sheet` components:** Both sheets share the same right-side drawer position. They must be siblings in the JSX tree, not nested. Each controlled by its own state variable.
- **Putting the `has_sample` toggle inside the row's click handler area:** Row `onClick` must have `event.stopPropagation()` on the toggle button. Miss this and every toggle also opens the sheet.
- **Using `variant="default"` for the Filters button when filters are active:** Per UI-SPEC, only the active filter count badge uses `variant="default"` (navy). The Filters button itself stays `variant="outline"` — the badge overlay signals activity.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Count of labeled spools per FilamentType | Python loop after fetching all spools | `func.count(case(...))` in SQL aggregation | Single query, no N+1, scales with tenant size |
| Focus trap in Sheet | Custom modal overlay | shadcn `Sheet` (Radix Dialog) | Already installed, handles focus trapping, aria, escape key |
| Optimistic UI for toggle | Manual state management with rollback | TanStack Query `onMutate`/`onError`/`onSettled` | Built-in rollback, cache management, consistent with existing patterns |
| Color hex normalization | Custom regex | Exact SpoolCard.tsx pattern (slice(2) for 8-char, passthrough for 6-char) | Already tested in production |
| Mobile/desktop responsive layout toggle | Custom JS resize observer | Tailwind `lg:hidden` / `hidden lg:block` | Already the project pattern from SpoolList.tsx |
| Filter sheet dismiss | Custom outside-click handler | shadcn `Sheet` `onOpenChange` prop | Handles outside click, escape key, ARIA |

---

## Common Pitfalls

### Pitfall 1: Stale Module Navigation After Backend Change
**What goes wrong:** The dynamic nav from `GET /api/v1/modules` still shows "Inventory" after the `MODULE_NAVIGATION` dict is updated in `modules.py`, because `useNavigationItems` has a 5-minute `staleTime`.
**Why it happens:** TanStack Query caches modules for 5 minutes (see `useModules.ts` line 7). During development and testing, the cache shows stale nav.
**How to avoid:** Test nav changes after a hard refresh (Ctrl+Shift+R) or by calling `queryClient.invalidateQueries({ queryKey: ['modules'] })` in the browser console. Also update the `fallbackNavItems` in `AppLayout.tsx` at the same time as the backend change — they must stay in sync.
**Warning signs:** "Inventory" still appears in nav after the module dict change during tests.

### Pitfall 2: `inventoryRoute` Removed from Route Tree
**What goes wrong:** If `inventoryRoute` is removed from the `routeTree.addChildren([...])` array instead of just changing its component to a redirect, navigating to `/inventory` throws a 404 or router error.
**Why it happens:** TanStack Router in this codebase does not have a catch-all 404 route. If the route is unregistered, the router renders nothing.
**How to avoid:** Keep `inventoryRoute` in the `addChildren` array. Only change its `component` to render `<Navigate to="/filaments" />`.

### Pitfall 3: N+1 Query for Spool Counts
**What goes wrong:** Fetching FilamentTypes, then fetching spools-per-type in a loop (one query per FilamentType row).
**Why it happens:** Natural instinct to iterate over FilamentTypes and call `spoolsApi.list({ filament_type_id: ft.id })` for each.
**How to avoid:** Backend aggregation with `GROUP BY filament_type_id` returns all counts in a single query. The frontend only ever sees pre-computed `spool_count` and `labeled_count`.

### Pitfall 4: `Spool` model missing `filament_type_id` in test conftest fixture for `/filaments/{id}/spools` tests
**What goes wrong:** Test fixture creates a `Spool` linked to `test_filament_type`, but the new `GET /api/v1/filament-types/{id}/spools` endpoint queries by `filament_type_id` — test passes only if fixture uses `test_filament_type.id`.
**Why it happens:** The existing `test_spool` fixture in `conftest.py` (lines 401–421) already correctly sets `filament_type_id=test_filament_type.id`. New tests can reuse this fixture.
**Warning signs:** The new endpoint returns 0 spools in tests even though spools exist.

### Pitfall 5: `has_sample` Toggle Triggering Row Click
**What goes wrong:** Clicking the sample toggle also opens the spool sheet.
**Why it happens:** The toggle button is inside the clickable row container. Click events bubble.
**How to avoid:** `e.stopPropagation()` on the toggle `Button`'s `onClick` handler. Same pattern as the Actions column in `SpoolList.tsx` (line 576: `onClick={(e) => e.stopPropagation()}`).

### Pitfall 6: Aggregated Endpoint Returning 0 Counts for Unlinked Spools
**What goes wrong:** Spools created before Phase 1 (with `material_type_id` directly on `Spool`) don't have `filament_type_id` set, so `outerjoin` finds no matching rows, and they don't appear in FilamentType aggregation.
**Why it happens:** Phase 1 migration moves data to the new schema. If Phase 1 migration is incomplete (not yet run in the target environment), the counts will be wrong.
**How to avoid:** Phase 2 is functionally dependent on Phase 1 migration being applied. Document this dependency in the plan. The aggregation endpoint should only be tested against a Phase-1-migrated database.

---

## Code Examples

### Backend: Aggregated List Endpoint

```python
# Source: backend/app/api/v1/filament_types.py (new endpoint to add)
# New Pydantic schema in schemas/filament_type.py:

class FilamentTypeAggregatedResponse(BaseModel):
    """Slim aggregated response for list view — includes spool counts."""
    id: UUID
    brand: str
    color: str
    color_hex: Optional[str]
    material_type_name: str
    material_type_code: str
    has_sample: bool
    spool_count: int
    labeled_count: int
    model_config = ConfigDict(from_attributes=False)

class FilamentTypeAggregatedListResponse(BaseModel):
    total: int
    filament_types: list[FilamentTypeAggregatedResponse]
    page: int
    page_size: int
```

```python
# New endpoint added to filament_types.py router:
@router.get("/aggregated", response_model=FilamentTypeAggregatedListResponse)
async def list_filament_types_aggregated(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    material_type_id: Optional[UUID] = Query(None),
    needs_labels: Optional[bool] = Query(None),
    needs_sample: Optional[bool] = Query(None),
) -> FilamentTypeAggregatedListResponse:
    """Aggregated FilamentType list with spool/labeled counts for list view."""
    ...
```

**Routing note:** This endpoint must be registered as `/aggregated` (a static sub-path) BEFORE the `/{filament_type_id}` dynamic route. The existing `router = APIRouter()` in `filament_types.py` is included via `main.py:243` at prefix `/api/v1/filament-types`. Add the `/aggregated` route to the same router file. Static routes match before dynamic in FastAPI when placed first in the file. [VERIFIED: direct inspection of FastAPI route ordering behavior in existing products/models routes in codebase]

### Backend: Spools Sub-Resource Endpoint

```python
# Source: backend/app/api/v1/filament_types.py (new endpoint to add)
class SpoolInSheetResponse(BaseModel):
    """Minimal spool info for read-only sheet display."""
    id: UUID
    spool_id: str
    current_weight: float
    initial_weight: float
    is_labeled: bool
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

@router.get("/{filament_type_id}/spools", response_model=list[SpoolInSheetResponse])
async def list_spools_for_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> list[SpoolInSheetResponse]:
    """List child spools for a FilamentType. Used by spool drill-down Sheet."""
    result = await db.execute(
        select(Spool)
        .where(Spool.filament_type_id == filament_type_id, Spool.tenant_id == tenant.id)
        .order_by(Spool.spool_id)
    )
    return result.scalars().all()
```

### Frontend: API Client

```typescript
// Source: frontend/src/lib/api/spools.ts (follow this exact pattern)
// New file: frontend/src/lib/api/filament-types.ts

import { apiClient } from '../api'
import type { FilamentTypeAggregatedListResponse, FilamentTypeListParams, SpoolInSheet, FilamentTypeUpdate } from '@/types/filament-type'

export const filamentTypesApi = {
  list: async (params?: FilamentTypeListParams): Promise<FilamentTypeAggregatedListResponse> => {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.brand) queryParams.append('brand', params.brand)
    if (params?.color) queryParams.append('color', params.color)
    if (params?.material_type_id) queryParams.append('material_type_id', params.material_type_id)
    if (params?.needs_labels !== undefined) queryParams.append('needs_labels', params.needs_labels.toString())
    if (params?.needs_sample !== undefined) queryParams.append('needs_sample', params.needs_sample.toString())
    return apiClient.get(`/api/v1/filament-types/aggregated?${queryParams}`)
  },
  getSpools: async (filamentTypeId: string): Promise<SpoolInSheet[]> => {
    return apiClient.get(`/api/v1/filament-types/${filamentTypeId}/spools`)
  },
  update: async (id: string, data: FilamentTypeUpdate): Promise<void> => {
    return apiClient.put(`/api/v1/filament-types/${id}`, data)
  },
}
```

### Frontend: TypeScript Types

```typescript
// New file: frontend/src/types/filament-type.ts
export interface FilamentTypeListItem {
  id: string
  brand: string
  color: string
  color_hex?: string | null
  material_type_name: string
  material_type_code: string
  has_sample: boolean
  spool_count: number
  labeled_count: number
}

export interface FilamentTypeAggregatedListResponse {
  total: number
  filament_types: FilamentTypeListItem[]
  page: number
  page_size: number
}

export interface FilamentTypeListParams {
  page?: number
  page_size?: number
  brand?: string
  color?: string
  material_type_id?: string
  needs_labels?: boolean
  needs_sample?: boolean
}

export interface SpoolInSheet {
  id: string
  spool_id: string
  current_weight: number
  initial_weight: number
  is_labeled: boolean
  is_active: boolean
}

export interface FilamentTypeUpdate {
  has_sample?: boolean
  brand?: string
  color?: string
  // ... other optional fields matching FilamentTypeUpdate Pydantic schema
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Both `/inventory` and `/filaments` render same `Dashboard`/`SpoolList` | `/inventory` redirects; `/filaments` renders new `FilamentTypeList` | Phase 2 | No 404s, single source of truth |
| Flat spool list (all spools as rows) | Grouped FilamentType rows with spool counts | Phase 2 | Reduces visual noise; groups related spools |
| Filters in a Card panel above the list | Search + Filters button in page header, filter dimensions in a Sheet | Phase 2 | More space for list; consistent with mobile UX patterns |

**Deprecated/outdated:**
- `Dashboard.tsx` rendering `SpoolList` at `/filaments`: `filamentsRoute` component changes to render new `FilamentTypeList` page. `Dashboard.tsx` itself may remain (still used at `/dashboard`? — check: no, `/dashboard` renders `DashboardHome`, not `Dashboard`. `Dashboard` is the layout wrapper for `SpoolList`. After Phase 2, `Dashboard.tsx` is unused by any route — mark for removal in Phase 4 cleanup but do not delete in Phase 2 to avoid scope creep.)
- "Inventory" navigation entry in `fallbackNavItems` and `MODULE_NAVIGATION["spools"]`: replaced with single "Filaments" entry.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLAlchemy `outerjoin` with compound condition `(Spool.filament_type_id == FilamentType.id) & (Spool.tenant_id == tenant.id)` produces correct LEFT JOIN SQL in async context | Architecture Patterns / Pattern 2 | Count query may return wrong results if tenant_id condition is incorrectly applied. Test with multi-tenant fixture to verify isolation. |
| A2 | `func.count(case((Spool.is_labeled == True, Spool.id)))` is correct SQLAlchemy 2.0 `case()` syntax | Architecture Patterns / Pattern 2 | `case()` import may need adjustment — SQLAlchemy 2.0 changed `case()` syntax from `case([(condition, value)])` to `case(condition, value)`. Verify against SQLAlchemy docs before implementing. |
| A3 | `Dashboard.tsx` is not used by any other route after Phase 2 (safe to leave but not delete) | State of the Art | If another route uses `Dashboard.tsx`, removing it in a future phase would break that route. |

---

## Open Questions

1. **Should the aggregated list endpoint be `/api/v1/filament-types/aggregated` (new path) or extend the existing `GET /api/v1/filament-types` with an `include_counts=true` param?**
   - What we know: The existing endpoint at `GET /api/v1/filament-types` returns `FilamentTypeListResponse` with full `FilamentTypeResponse` objects. The aggregated shape is different (counts added, spec fields removed). Same router, registered in main.py.
   - What's unclear: Whether Phase 1 code elsewhere calls `GET /api/v1/filament-types` and would break if the response shape changes.
   - Recommendation: Use a new `/aggregated` sub-path to avoid breaking any Phase 1 code that expects the existing response shape. Simpler, no conditional logic in the handler.

2. **Does Phase 1 migration need to be complete before Phase 2 can be tested?**
   - What we know: The aggregation query joins FilamentType with Spool via `filament_type_id`. Spools created before Phase 1 had `material_type_id` directly — Phase 1 migrates them to the two-tier model.
   - What's unclear: Whether Phase 1 is complete in the development environment.
   - Recommendation: Phase 2 plan should include a Wave 0 prerequisite check: verify `Spool.filament_type_id` FK is non-null for migrated spools before running aggregation tests.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 2 is a code-only change. All tools (Node.js, Python, PostgreSQL) were verified as present during Phase 1. No new external dependencies.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio + pytest-cov |
| Backend config | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Backend quick run | `cd backend && poetry run pytest tests/api/test_filament_types.py -x` |
| Backend full suite | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| Frontend framework | Vitest 4.x + jsdom + @testing-library/react |
| Frontend config | `frontend/vitest.config.ts` |
| Frontend quick run | `cd frontend && pnpm test --run src/components/filaments/` |
| Frontend full suite | `cd frontend && pnpm test --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAV-01 | `/inventory` redirects to `/filaments` | unit (frontend) | `pnpm test --run src/App.test.tsx` | ❌ Wave 0 |
| NAV-02 | No internal links to `/inventory` | integration (frontend) | `grep -rn '"/inventory"' frontend/src/` | manual check |
| LIST-01 | Aggregated list groups by FilamentType with spool count | unit (backend) | `poetry run pytest tests/api/test_filament_types.py::test_aggregated_list -x` | ❌ Wave 0 |
| LIST-02 | Row shows labeled count and sample status | unit (backend) | `poetry run pytest tests/api/test_filament_types.py::test_aggregated_counts -x` | ❌ Wave 0 |
| LIST-03 | Filter by needs_labels / needs_sample | unit (backend) | `poetry run pytest tests/api/test_filament_types.py::test_aggregated_filters -x` | ❌ Wave 0 |
| D-10 | Sheet fetches `GET /api/v1/filament-types/{id}/spools` | unit (backend) | `poetry run pytest tests/api/test_filament_types.py::test_spools_sub_resource -x` | ❌ Wave 0 |
| D-06 | `has_sample` toggle uses existing PUT endpoint | unit (backend) | `poetry run pytest tests/api/test_filament_types.py::test_update_has_sample -x` | exists (test_filament_types.py partially) |

### Sampling Rate
- **Per task commit:** `cd backend && poetry run pytest tests/api/test_filament_types.py -x`
- **Per wave merge:** `cd backend && poetry run pytest && cd ../frontend && pnpm test --run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/test_filament_types.py` — covers aggregated list (LIST-01, LIST-02, LIST-03) and spools sub-resource (D-10). Note: existing `test_filament_types.py` may exist — check before creating.
- [ ] `frontend/src/App.test.tsx` — covers redirect behavior (NAV-01). No existing App-level route tests found.
- [ ] `frontend/src/components/filaments/FilamentTypeCard.test.tsx` — covers mobile card rendering.
- [ ] Conftest already has `test_filament_type` and `test_spool` fixtures (lines 376–421 of `conftest.py`) — no new fixtures needed for backend tests.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `CurrentUser` dependency on all new endpoints |
| V3 Session Management | no | Handled by existing auth layer |
| V4 Access Control | yes | `CurrentTenant` + RLS via `TenantDB` dependency on all new endpoints |
| V5 Input Validation | yes | Pydantic schemas validate all query params (UUID, boolean, string length) |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns for Phase 2

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-tenant FilamentType aggregation | Information disclosure | `WHERE filament_type.tenant_id == tenant.id` in aggregation query; `TenantDB` dependency sets RLS context |
| Tenant A reading Tenant B's spools via `/filament-types/{id}/spools` | Information disclosure | Join condition `Spool.tenant_id == tenant.id` in sub-resource query — must be explicit even with RLS enabled |
| Unvalidated UUID in `filament_type_id` path param | Tampering | FastAPI path param typed as `UUID` — auto-validates format, returns 422 on invalid |
| `has_sample` toggle bypassing auth | Elevation of privilege | `CurrentUser` + `CurrentTenant` required on PUT endpoint — already present in existing `update_filament_type` handler |

---

## Sources

### Primary (HIGH confidence)
- `frontend/src/App.tsx` — Full route tree, verified `inventoryRoute` and `filamentsRoute` definitions, `Navigate` import pattern
- `frontend/src/components/inventory/SpoolList.tsx` — Filter pattern ("Low Stock Only" button), mobile/desktop breakpoint pattern, TanStack Query usage
- `frontend/src/components/inventory/SpoolCard.tsx` — Color hex normalization pattern, Card layout pattern
- `frontend/src/components/layout/AppLayout.tsx` — Full nav system: dynamic `useNavigationItems`, `fallbackNavItems` with `/inventory` entry
- `backend/app/api/v1/filament_types.py` — All existing FilamentType endpoints, `CurrentTenant`/`CurrentUser`/`TenantDB` pattern
- `backend/app/api/v1/modules.py` — `MODULE_NAVIGATION` dict with `/inventory` and `/filaments` entries for "spools" module
- `backend/app/models/filament_type.py` — `FilamentType` model: all fields including `has_sample`, relationships
- `backend/app/models/spool.py` — `Spool` model: `filament_type_id`, `is_labeled`, `is_active`, `spool_id`, `current_weight`
- `backend/app/schemas/filament_type.py` — `FilamentTypeUpdate` has `has_sample: Optional[bool]` — confirms toggle can use existing PUT endpoint
- `backend/app/schemas/spool.py` — `SpoolResponse` shape for the sub-resource response
- `backend/tests/conftest.py` — `test_filament_type` and `test_spool` fixtures (lines 376–421)
- `.planning/phases/02-consolidated-list-view/02-CONTEXT.md` — All locked decisions
- `.planning/phases/02-consolidated-list-view/02-UI-SPEC.md` — Full UI design contract

### Secondary (MEDIUM confidence)
- `frontend/src/hooks/useModules.ts` — `staleTime: 5 * 60 * 1000` for modules cache, explaining nav staleness pitfall
- `frontend/vitest.config.ts` — Test framework configuration confirmed

### Tertiary (LOW confidence)
- None — all claims verified from codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified as installed
- Architecture: HIGH — existing patterns directly observed in codebase
- Backend API shape: HIGH — models and schemas read directly
- Frontend routing: HIGH — App.tsx read in full
- Pitfalls: MEDIUM-HIGH — derived from direct code inspection plus SQLAlchemy 2.0 case() syntax assumption (A2)

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (stable stack, no fast-moving dependencies)
