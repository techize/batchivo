# Phase 2: Consolidated List View - Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/App.tsx` (modify) | config/router | request-response | itself (lines 219–242) | self |
| `frontend/src/components/layout/AppLayout.tsx` (modify) | component | event-driven | itself (lines 115–128) | self |
| `backend/app/api/v1/modules.py` (modify) | config | request-response | itself (lines 78–80) | self |
| `frontend/src/types/filament-type.ts` (new) | utility/types | — | `frontend/src/types/spool.ts` | exact |
| `frontend/src/lib/api/filament-types.ts` (new) | utility/api-client | request-response | `frontend/src/lib/api/spools.ts` | exact |
| `frontend/src/hooks/useFilamentTypes.ts` (new) | hook | request-response | `frontend/src/hooks/useModules.ts` | role-match |
| `frontend/src/pages/FilamentLibrary.tsx` (new) | component/page | request-response | `frontend/src/components/inventory/SpoolList.tsx` | exact |
| `frontend/src/components/filaments/FilamentTypeCard.tsx` (new) | component | request-response | `frontend/src/components/inventory/SpoolCard.tsx` | exact |
| `frontend/src/components/filaments/FilamentTypeRow.tsx` (new) | component | request-response | `frontend/src/components/inventory/SpoolList.tsx` lines 457–633 | exact |
| `frontend/src/components/filaments/FilamentTypeSpoolSheet.tsx` (new) | component | request-response | shadcn Sheet usage in `AppLayout.tsx` lines 44–48 | role-match |
| `frontend/src/components/filaments/FilamentTypeFilterSheet.tsx` (new) | component | request-response | `SpoolList.tsx` filter card (lines 281–362) | role-match |
| `backend/app/schemas/filament_type.py` (modify) | schema | — | itself + `backend/app/schemas/spool.py` | self |
| `backend/app/api/v1/filament_types.py` (modify) | controller | CRUD | itself (lines 68–116) | self |
| `backend/tests/integration/test_filament_types_api.py` (modify) | test | CRUD | itself (lines 83–104) | self |

---

## Pattern Assignments

### `frontend/src/App.tsx` — inventoryRoute redirect + filamentsRoute page swap

**Analog:** itself (existing `inventoryRoute` and `filamentsRoute`, lines 219–242)

**Existing pattern to copy** (lines 219–242):
```typescript
// Inventory route (filament spools)
const inventoryRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/inventory',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Dashboard />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Filaments route (alias for inventory - spools management)
const filamentsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Dashboard />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})
```

**Change required — inventoryRoute becomes redirect, filamentsRoute renders new page:**
```typescript
// inventoryRoute: keep in addChildren array, change component to redirect
const inventoryRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/inventory',
  component: () => <Navigate to="/filaments" />,
  // NOTE: No ProtectedRoute wrapper needed — Navigate fires immediately
})

// filamentsRoute: change Dashboard to FilamentLibrary
const filamentsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <FilamentLibrary />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})
```

**Navigate import** (line 11 — already present):
```typescript
import { Router, Route, RootRoute, RouterProvider, Navigate, Outlet } from '@tanstack/react-router'
```

**Key constraint:** `inventoryRoute` MUST remain in `routeTree.addChildren([...])` (line 701). Removing it causes a router error because no catch-all 404 route exists.

---

### `frontend/src/components/layout/AppLayout.tsx` — remove "Inventory" from fallbackNavItems

**Analog:** itself (lines 115–128)

**Existing pattern** (lines 115–128):
```typescript
const fallbackNavItems = [
  { path: '/dashboard', label: 'Dashboard', icon: 'layout-dashboard', exact: true },
  { path: '/products', label: 'Products', icon: 'package' },
  { path: '/models', label: 'Models', icon: 'layers' },
  { path: '/designers', label: 'Designers', icon: 'brush' },
  { path: '/categories', label: 'Categories', icon: 'folder-open' },
  { path: '/production-runs', label: 'Runs', icon: 'play' },
  { path: '/inventory', label: 'Inventory', icon: 'box', exact: true },   // REMOVE this line
  { path: '/dashboard/printers', label: 'Fleet', icon: 'activity' },
  { path: '/printers', label: 'Printers', icon: 'printer' },
  { path: '/consumables', label: 'Consumables', icon: 'wrench' },
  { path: '/sales-channels', label: 'Channels', icon: 'store' },
  { path: '/orders', label: 'Orders', icon: 'shopping-bag' },
]
```

**Change required:** Remove the `/inventory` entry. The `/filaments` entry is already served by the dynamic nav from `MODULE_NAVIGATION`. Ensure the `FlaskConical` or `box` icon is used for it consistently.

---

### `backend/app/api/v1/modules.py` — fix MODULE_NAVIGATION["spools"]

**Analog:** itself (lines 78–80)

**Existing pattern** (lines 78–80):
```python
"spools": [
    {"path": "/inventory", "label": "Inventory", "icon": "box", "exact": True},
    {"path": "/filaments", "label": "Filaments", "icon": "box", "exact": False},
],
```

**Change required:** Replace both entries with a single Filaments entry:
```python
"spools": [
    {"path": "/filaments", "label": "Filaments", "icon": "box", "exact": False},
],
```

---

### `frontend/src/types/filament-type.ts` (new file)

**Analog:** `frontend/src/types/spool.ts`

**Imports/structure pattern** (spool.ts lines 1–12):
```typescript
/**
 * TypeScript types for FilamentType API
 * These match the Pydantic schemas in backend/app/schemas/filament_type.py
 */

// Base interfaces follow same naming convention as spool.ts
export interface FilamentTypeListItem { ... }
export interface FilamentTypeAggregatedListResponse { ... }
export interface FilamentTypeListParams { ... }
export interface SpoolInSheet { ... }
export interface FilamentTypeUpdate { ... }
```

**Full type definitions to implement** (from RESEARCH.md):
```typescript
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
  color_hex?: string | null
  material_type_id?: string
  finish?: string | null
  diameter?: number
  extruder_temp?: number | null
  bed_temp?: number | null
  translucent?: boolean
  glow?: boolean
  notes?: string | null
}
```

---

### `frontend/src/lib/api/filament-types.ts` (new file)

**Analog:** `frontend/src/lib/api/spools.ts`

**Imports pattern** (spools.ts lines 1–9):
```typescript
import { apiClient } from '../api'
import type {
  FilamentTypeAggregatedListResponse,
  FilamentTypeListParams,
  FilamentTypeListItem,
  SpoolInSheet,
  FilamentTypeUpdate,
} from '@/types/filament-type'
```

**Core API object pattern** (spools.ts lines 15–91 — named object with typed async methods):
```typescript
/**
 * FilamentTypes API Client
 * Handles FilamentType list and spool drill-down API operations
 */
export const filamentTypesApi = {
  /**
   * List filament types (aggregated with spool counts)
   */
  list: async (params?: FilamentTypeListParams): Promise<FilamentTypeAggregatedListResponse> => {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.brand) queryParams.append('brand', params.brand)
    if (params?.color) queryParams.append('color', params.color)
    if (params?.material_type_id) queryParams.append('material_type_id', params.material_type_id)
    if (params?.needs_labels !== undefined) queryParams.append('needs_labels', params.needs_labels.toString())
    if (params?.needs_sample !== undefined) queryParams.append('needs_sample', params.needs_sample.toString())
    const queryString = queryParams.toString()
    const url = `/api/v1/filament-types/aggregated${queryString ? `?${queryString}` : ''}`
    return apiClient.get<FilamentTypeAggregatedListResponse>(url)
  },

  /**
   * Get child spools for a FilamentType (sheet drill-down)
   */
  getSpools: async (filamentTypeId: string): Promise<SpoolInSheet[]> => {
    return apiClient.get<SpoolInSheet[]>(`/api/v1/filament-types/${filamentTypeId}/spools`)
  },

  /**
   * Update a filament type (used for has_sample toggle)
   */
  update: async (id: string, data: FilamentTypeUpdate): Promise<FilamentTypeListItem> => {
    return apiClient.put<FilamentTypeListItem>(`/api/v1/filament-types/${id}`, data)
  },
}
```

**Key detail from spools.ts (line 30–32):** Build URL with conditional query string — `?${queryString}` only when non-empty.

---

### `frontend/src/hooks/useFilamentTypes.ts` (new file)

**Analog:** `frontend/src/hooks/useModules.ts`

**Imports pattern** (useModules.ts lines 8–10):
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { filamentTypesApi } from '@/lib/api/filament-types'
import type { FilamentTypeAggregatedListResponse, FilamentTypeListParams, FilamentTypeUpdate } from '@/types/filament-type'
```

**Core hook pattern** (useModules.ts lines 17–26 — useQuery with explicit options):
```typescript
/**
 * Hook to fetch aggregated FilamentType list with spool counts.
 */
export function useFilamentTypes(params: FilamentTypeListParams) {
  return useQuery<FilamentTypeAggregatedListResponse>({
    queryKey: ['filament-types', params],
    queryFn: () => filamentTypesApi.list(params),
  })
}

/**
 * Hook to fetch child spools for a FilamentType.
 * Only fetches when filamentTypeId is non-null (i.e., sheet is open).
 */
export function useFilamentTypeSpools(filamentTypeId: string | null) {
  return useQuery({
    queryKey: ['filament-type-spools', filamentTypeId],
    queryFn: () => filamentTypesApi.getSpools(filamentTypeId!),
    enabled: filamentTypeId !== null,
  })
}

/**
 * Mutation for toggling has_sample on a FilamentType row.
 * Uses optimistic update: immediately flips the value, rolls back on error.
 */
export function useToggleHasSample(params: FilamentTypeListParams) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, hasSample }: { id: string; hasSample: boolean }) =>
      filamentTypesApi.update(id, { has_sample: hasSample }),
    onMutate: async ({ id, hasSample }) => {
      await queryClient.cancelQueries({ queryKey: ['filament-types'] })
      const previous = queryClient.getQueryData(['filament-types', params])
      queryClient.setQueryData(
        ['filament-types', params],
        (old: FilamentTypeAggregatedListResponse) => ({
          ...old,
          filament_types: old.filament_types.map((ft) =>
            ft.id === id ? { ...ft, has_sample: hasSample } : ft
          ),
        })
      )
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
}
```

---

### `frontend/src/pages/FilamentLibrary.tsx` (new file)

**Analog:** `frontend/src/components/inventory/SpoolList.tsx`

**Imports pattern** (SpoolList.tsx lines 1–41 — adapt, drop offline/indexeddb imports):
```typescript
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useFilamentTypes, useToggleHasSample } from '@/hooks/useFilamentTypes'
import type { FilamentTypeListParams } from '@/types/filament-type'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Search, Filter } from 'lucide-react'
import { FilamentTypeCard } from '@/components/filaments/FilamentTypeCard'
import { FilamentTypeRow } from '@/components/filaments/FilamentTypeRow'
import { FilamentTypeSpoolSheet } from '@/components/filaments/FilamentTypeSpoolSheet'
import { FilamentTypeFilterSheet } from '@/components/filaments/FilamentTypeFilterSheet'
```

**State pattern** (SpoolList.tsx lines 47–63 — two independent sheet state vars, no nesting):
```typescript
// Two independent sheet state vars — must NOT be nested (Radix focus trap constraint)
const [spoolSheetFilamentTypeId, setSpoolSheetFilamentTypeId] = useState<string | null>(null)
const [filterSheetOpen, setFilterSheetOpen] = useState(false)
const [params, setParams] = useState<FilamentTypeListParams>({
  page: 1,
  page_size: 20,
})
```

**Filter toggle pattern** (SpoolList.tsx lines 231–233 — existing "Low Stock Only" toggle):
```typescript
// Pattern from SpoolList.tsx toggleLowStock (line 231)
const toggleNeedsLabels = () => {
  setParams((prev) => ({ ...prev, needs_labels: prev.needs_labels ? undefined : true, page: 1 }))
}
const toggleNeedsSample = () => {
  setParams((prev) => ({ ...prev, needs_sample: prev.needs_sample ? undefined : true, page: 1 }))
}
```

**Header pattern** (SpoolList.tsx lines 258–278):
```typescript
<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
  <div>
    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Filament Library</h1>
    <p className="text-muted-foreground text-sm sm:text-base">
      Your filament collection, grouped by type
    </p>
  </div>
  {/* Search + Filters button side-by-side (D-14) */}
  <div className="flex gap-2 w-full sm:w-auto">
    <div className="relative flex-1 sm:flex-none sm:w-64">
      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input placeholder="Search brand or colour..." className="pl-8" ... />
    </div>
    <Button variant="outline" onClick={() => setFilterSheetOpen(true)}>
      <Filter className="h-4 w-4 mr-2" />
      Filters
      {activeFilterCount > 0 && (
        <Badge variant="default" className="ml-2 h-5 w-5 p-0 text-xs flex items-center justify-center">
          {activeFilterCount}
        </Badge>
      )}
    </Button>
  </div>
</div>
```

**Mobile/desktop split pattern** (SpoolList.tsx lines 409–439):
```typescript
{/* Mobile Card View */}
<div className="lg:hidden space-y-4">
  {filamentTypes.map((ft) => (
    <FilamentTypeCard key={ft.id} filamentType={ft} ... />
  ))}
</div>

{/* Desktop Table View */}
<div className="hidden lg:block">
  <Table>
    <TableHeader>...</TableHeader>
    <TableBody>
      {filamentTypes.map((ft) => (
        <FilamentTypeRow key={ft.id} filamentType={ft} ... />
      ))}
    </TableBody>
  </Table>
</div>
```

**Loading/error/empty state pattern** (SpoolList.tsx lines 380–405):
```typescript
{isLoading && (
  <div className="flex items-center justify-center py-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    <span className="ml-3 text-muted-foreground">Loading filaments...</span>
  </div>
)}
{isError && (
  <div className="bg-destructive/10 border border-destructive rounded-md p-4">
    <p className="text-destructive font-medium">Error loading filaments</p>
    <p className="text-sm text-muted-foreground mt-2">
      {error instanceof Error ? error.message : 'Unknown error'}
    </p>
  </div>
)}
{data && filamentTypes.length === 0 && (
  <div className="text-center py-8 text-muted-foreground">
    <p className="text-lg font-medium">No filaments found</p>
    <p className="text-sm mt-2">
      {hasActiveFilters ? 'Try adjusting your filters' : 'Get started by adding your first filament type'}
    </p>
  </div>
)}
```

**Sheet sibling pattern** (end of JSX — both sheets are siblings, not nested):
```typescript
{/* Spool drill-down sheet */}
<FilamentTypeSpoolSheet
  filamentTypeId={spoolSheetFilamentTypeId}
  onClose={() => setSpoolSheetFilamentTypeId(null)}
/>

{/* Filter sheet */}
<FilamentTypeFilterSheet
  open={filterSheetOpen}
  onOpenChange={setFilterSheetOpen}
  params={params}
  onParamsChange={(newParams) => setParams({ ...newParams, page: 1 })}
/>
```

---

### `frontend/src/components/filaments/FilamentTypeCard.tsx` (new file)

**Analog:** `frontend/src/components/inventory/SpoolCard.tsx`

**Imports pattern** (SpoolCard.tsx lines 1–9 — drop framer-motion and react-swipeable, no swipe actions):
```typescript
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { TestTube2 } from 'lucide-react'    // for has_sample toggle icon
import type { FilamentTypeListItem } from '@/types/filament-type'
```

**Props interface pattern** (SpoolCard.tsx lines 11–18):
```typescript
interface FilamentTypeCardProps {
  filamentType: FilamentTypeListItem
  onRowClick: (id: string) => void          // opens SpoolSheet
  onToggleSample: (id: string, hasSample: boolean) => void
  isTogglingId?: string | null
}
```

**Color swatch pattern** (SpoolCard.tsx lines 89–98 — exact hex normalization to reuse):
```typescript
// Color swatch: 12px circle for list view (w-3 h-3 rounded-full)
// SpoolCard uses 40px square (w-10 h-10 rounded-md) — size only differs
{filamentType.color_hex && (
  <div
    className="w-3 h-3 rounded-full border border-border flex-shrink-0"
    style={{
      backgroundColor: `#${filamentType.color_hex.length === 8
        ? filamentType.color_hex.slice(2)
        : filamentType.color_hex}`
    }}
    title={`#${filamentType.color_hex}`}
  />
)}
```

**Badge pattern** (SpoolCard.tsx lines 143–163 — reuse Badge for spool count, labeled count, sample status):
```typescript
<div className="flex flex-wrap gap-2">
  <Badge variant="secondary">{filamentType.spool_count} spools</Badge>
  <Badge variant={filamentType.labeled_count === filamentType.spool_count ? 'success' : 'warning'}>
    {filamentType.labeled_count}/{filamentType.spool_count} labeled
  </Badge>
  <Badge variant={filamentType.has_sample ? 'success' : 'outline'}>
    {filamentType.has_sample ? 'Sample ✓' : 'Sample ✗'}
  </Badge>
</div>
```

**stopPropagation pattern for toggle** (SpoolList.tsx line 576 — must copy exactly):
```typescript
// has_sample toggle: stopPropagation prevents row click from also opening sheet
<Button
  variant="ghost"
  size="sm"
  onClick={(e) => {
    e.stopPropagation()   // REQUIRED — prevents row onClick from firing
    onToggleSample(filamentType.id, !filamentType.has_sample)
  }}
>
  <TestTube2 className="h-4 w-4" />
</Button>
```

---

### `frontend/src/components/filaments/FilamentTypeRow.tsx` (new file)

**Analog:** `frontend/src/components/inventory/SpoolList.tsx` (TableRow block, lines 457–633)

**Row pattern** (SpoolList.tsx lines 457–463):
```typescript
<TableRow
  key={ft.id}
  className="cursor-pointer hover:bg-muted/50"
  onClick={() => onRowClick(ft.id)}
>
```

**Actions column with stopPropagation** (SpoolList.tsx line 576):
```typescript
<TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
  {/* has_sample toggle goes here */}
  <Button variant="ghost" size="sm" onClick={(e) => {
    e.stopPropagation()
    onToggleSample(ft.id, !ft.has_sample)
  }}>
    <TestTube2 className="h-4 w-4" />
  </Button>
</TableCell>
```

**Table headers for FilamentType columns:**
```typescript
<TableHeader>
  <TableRow>
    <TableHead>Brand</TableHead>
    <TableHead>Colour</TableHead>
    <TableHead>Material</TableHead>
    <TableHead>Spools</TableHead>
    <TableHead>Labels</TableHead>
    <TableHead>Sample</TableHead>
    <TableHead className="text-right">Actions</TableHead>
  </TableRow>
</TableHeader>
```

---

### `frontend/src/components/filaments/FilamentTypeSpoolSheet.tsx` (new file)

**Analog:** `AppLayout.tsx` Sheet usage (lines 44–48 — shadcn Sheet import) + SpoolList.tsx ViewSpoolDialog pattern

**Imports pattern:**
```typescript
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { useFilamentTypeSpools } from '@/hooks/useFilamentTypes'
import type { FilamentTypeListItem } from '@/types/filament-type'
```

**Sheet open/close pattern** (AppLayout.tsx lines 44–48 — controlled via `open` + `onOpenChange`):
```typescript
interface FilamentTypeSpoolSheetProps {
  filamentTypeId: string | null
  filamentTypeName?: string       // for SheetTitle
  onClose: () => void
}

export function FilamentTypeSpoolSheet({ filamentTypeId, filamentTypeName, onClose }: FilamentTypeSpoolSheetProps) {
  const { data: spools, isLoading } = useFilamentTypeSpools(filamentTypeId)

  return (
    <Sheet open={filamentTypeId !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{filamentTypeName ?? 'Spools'}</SheetTitle>
          <SheetDescription>Individual spool records for this filament type</SheetDescription>
        </SheetHeader>
        {/* Read-only spool table: spool_id, current_weight, is_labeled, is_active */}
        {/* No Edit/Delete/Update Weight actions — deferred to Phase 4 */}
      </SheetContent>
    </Sheet>
  )
}
```

**Read-only table inside sheet** (SpoolList.tsx TableRow pattern, lines 457–475 — simplified, no onClick):
```typescript
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Spool ID</TableHead>
      <TableHead>Weight</TableHead>
      <TableHead>Labeled</TableHead>
      <TableHead>Active</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {spools?.map((spool) => (
      <TableRow key={spool.id}>
        <TableCell className="font-mono">{spool.spool_id}</TableCell>
        <TableCell>{spool.current_weight.toFixed(0)}g / {spool.initial_weight.toFixed(0)}g</TableCell>
        <TableCell>
          {spool.is_labeled
            ? <Badge variant="success">Labeled</Badge>
            : <Badge variant="warning">Needs label</Badge>
          }
        </TableCell>
        <TableCell>
          {spool.is_active
            ? <Badge variant="success">Active</Badge>
            : <Badge variant="secondary">Inactive</Badge>
          }
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

---

### `frontend/src/components/filaments/FilamentTypeFilterSheet.tsx` (new file)

**Analog:** `SpoolList.tsx` filter Card (lines 280–363) — adapted to Sheet layout

**Imports pattern:**
```typescript
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useQuery } from '@tanstack/react-query'
import { materialTypesApi } from '@/lib/api/spools'   // already exists
import type { FilamentTypeListParams } from '@/types/filament-type'
```

**Filter toggle button pattern** (SpoolList.tsx lines 300–316 — `variant="default"` when active, `variant="outline"` when inactive):
```typescript
<Button
  variant={params.needs_labels ? 'default' : 'outline'}
  onClick={() => onParamsChange({ ...params, needs_labels: params.needs_labels ? undefined : true })}
  size="sm"
>
  Needs labels
</Button>
<Button
  variant={params.needs_sample ? 'default' : 'outline'}
  onClick={() => onParamsChange({ ...params, needs_sample: params.needs_sample ? undefined : true })}
  size="sm"
>
  No sample
</Button>
```

**Material type select pattern** (SpoolList.tsx lines 323–338 — reuse same `materialTypesApi.list()` call):
```typescript
const { data: materialTypes } = useQuery({
  queryKey: ['material-types'],
  queryFn: () => materialTypesApi.list(),
})
```

---

### `backend/app/schemas/filament_type.py` (modify — add two new schemas)

**Analog:** itself (existing `FilamentTypeListResponse`, lines 95–102)

**Existing schema pattern to copy** (lines 80–102):
```python
class FilamentTypeResponse(FilamentTypeBase):
    """Schema for FilamentType responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    material_type_code: str = Field(..., description="Material code (PLA, PETG, etc.)")
    material_type_name: str = Field(..., description="Material full name")

    model_config = ConfigDict(from_attributes=True)


class FilamentTypeListResponse(BaseModel):
    """Schema for paginated FilamentType list."""

    total: int = Field(..., description="Total number of filament types")
    filament_types: list[FilamentTypeResponse] = Field(..., description="List of filament types")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
```

**New schemas to add** (mirror `FilamentTypeListResponse` naming pattern):
```python
class FilamentTypeAggregatedResponse(BaseModel):
    """Slim aggregated response for list view — includes spool counts, excludes spec fields."""

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
    """Paginated aggregated FilamentType list for the list view."""

    total: int = Field(..., description="Total number of filament types")
    filament_types: list[FilamentTypeAggregatedResponse] = Field(..., description="Aggregated list")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class SpoolInSheetResponse(BaseModel):
    """Minimal spool info for read-only sheet display."""

    id: UUID
    spool_id: str
    current_weight: float
    initial_weight: float
    is_labeled: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
```

---

### `backend/app/api/v1/filament_types.py` (modify — add two new endpoints)

**Analog:** itself (existing `list_filament_types`, lines 68–116)

**Imports additions** (lines 1–20 — add `case` to existing `func, select` import, add `Spool` model):
```python
from sqlalchemy import case, func, select    # add `case` to existing import
from app.models.spool import Spool           # add new import
from app.schemas.filament_type import (
    FilamentTypeCreate,
    FilamentTypeListResponse,
    FilamentTypeResponse,
    FilamentTypeUpdate,
    FilamentTypeAggregatedListResponse,      # add
    FilamentTypeAggregatedResponse,          # add
    SpoolInSheetResponse,                    # add
)
```

**New aggregated endpoint — MUST be placed before `/{filament_type_id}` route** (currently line 119):
```python
@router.get("/aggregated", response_model=FilamentTypeAggregatedListResponse)
async def list_filament_types_aggregated(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    brand: Optional[str] = Query(None, description="Filter by brand (text search)"),
    color: Optional[str] = Query(None, description="Filter by colour (text search)"),
    material_type_id: Optional[UUID] = Query(None, description="Filter by material type"),
    needs_labels: Optional[bool] = Query(None, description="Show only types with unlabeled spools"),
    needs_sample: Optional[bool] = Query(None, description="Show only types without a sample"),
) -> FilamentTypeAggregatedListResponse:
    """Aggregated FilamentType list with spool/labeled counts for the list view."""
    from app.models.material import MaterialType   # local import pattern (avoids circular)

    query = (
        select(
            FilamentType.id,
            FilamentType.brand,
            FilamentType.color,
            FilamentType.color_hex,
            FilamentType.has_sample,
            MaterialType.name.label("material_type_name"),
            MaterialType.code.label("material_type_code"),
            func.count(Spool.id).label("spool_count"),
            func.count(case((Spool.is_labeled == True, Spool.id))).label("labeled_count"),
        )
        .outerjoin(Spool, (Spool.filament_type_id == FilamentType.id) & (Spool.tenant_id == tenant.id))
        .outerjoin(MaterialType, MaterialType.id == FilamentType.material_type_id)
        .where(FilamentType.tenant_id == tenant.id)
        .group_by(
            FilamentType.id, FilamentType.brand, FilamentType.color, FilamentType.color_hex,
            FilamentType.has_sample, MaterialType.name, MaterialType.code,
        )
    )

    if brand:
        query = query.where(FilamentType.brand.ilike(f"%{brand}%"))
    if color:
        query = query.where(FilamentType.color.ilike(f"%{color}%"))
    if material_type_id:
        query = query.where(FilamentType.material_type_id == material_type_id)
    if needs_sample:
        query = query.where(FilamentType.has_sample == False)
    # needs_labels filter: requires a HAVING clause (spool count where not labeled > 0)
    # or a subquery — implement via subquery or add as a HAVING after aggregation

    # Count total
    count_subquery = query.subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(FilamentType.brand, FilamentType.color))
    rows = result.mappings().all()

    return FilamentTypeAggregatedListResponse(
        total=total,
        filament_types=[FilamentTypeAggregatedResponse(**row) for row in rows],
        page=page,
        page_size=page_size,
    )
```

**New spools sub-resource endpoint** (pattern from existing `get_filament_type`, lines 119–146):
```python
@router.get("/{filament_type_id}/spools", response_model=list[SpoolInSheetResponse])
async def list_spools_for_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> list[SpoolInSheetResponse]:
    """List child spools for a FilamentType. Used by the read-only spool sheet."""
    from app.models.spool import Spool  # local import

    # Verify FilamentType exists and belongs to tenant (authorization check)
    ft_result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = ft_result.scalar_one_or_none()
    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )

    result = await db.execute(
        select(Spool)
        .where(Spool.filament_type_id == filament_type_id, Spool.tenant_id == tenant.id)
        .order_by(Spool.spool_id)
    )
    spools = result.scalars().all()
    logger.info(f"Listed {len(spools)} spools for FilamentType {filament_type_id}")
    return [SpoolInSheetResponse.model_validate(s) for s in spools]
```

**Route ordering rule (CRITICAL):** `/aggregated` must appear in the file before `/{filament_type_id}` and `/{filament_type_id}/spools` must appear before any broader `/{filament_type_id}` catch. Static paths match before dynamic in FastAPI when ordered first. Confirmed from existing codebase pattern in products/models routes.

---

### `backend/tests/integration/test_filament_types_api.py` (modify — add new test class)

**Analog:** itself (existing `TestFilamentTypesEndpoints`, lines 21–198)

**Test class structure pattern** (lines 21–28):
```python
class TestFilamentTypeAggregatedEndpoints:
    """Integration tests for aggregated FilamentType endpoints."""

    # ============================================
    # GET /api/v1/filament-types/aggregated
    # ============================================

    @pytest.mark.asyncio
    async def test_aggregated_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_filament_type,   # fixture from conftest.py line 376
        test_spool,           # fixture from conftest.py line 400
    ):
        """Test aggregated list returns spool_count and labeled_count."""
        response = await client.get("/api/v1/filament-types/aggregated", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "filament_types" in data
        row = data["filament_types"][0]
        assert "spool_count" in row
        assert "labeled_count" in row
        assert "material_type_name" in row
        assert "has_sample" in row
```

**Auth test pattern** (lines 99–103):
```python
@pytest.mark.asyncio
async def test_aggregated_requires_auth(self, unauthenticated_client: AsyncClient):
    """Test aggregated list without auth returns 401."""
    response = await unauthenticated_client.get("/api/v1/filament-types/aggregated")
    assert response.status_code in [401, 403]
```

**Sub-resource test pattern:**
```python
# ============================================
# GET /api/v1/filament-types/{id}/spools
# ============================================

@pytest.mark.asyncio
async def test_spools_sub_resource(
    self,
    client: AsyncClient,
    auth_headers: dict,
    test_filament_type,
    test_spool,          # already linked via test_spool.filament_type_id=test_filament_type.id
):
    """Test spools sub-resource returns child spools for a FilamentType."""
    response = await client.get(
        f"/api/v1/filament-types/{test_filament_type.id}/spools",
        headers=auth_headers,
    )
    assert response.status_code == 200
    spools = response.json()
    assert isinstance(spools, list)
    assert len(spools) >= 1
    assert spools[0]["spool_id"] == "TEST-SPOOL-001"
```

**Conftest fixtures (lines 376–418 — no new fixtures needed, reuse as-is):**
- `test_filament_type` — creates FilamentType with `test_tenant.id` and `test_material_type.id`
- `test_spool` — creates Spool with `filament_type_id=test_filament_type.id` and `is_labeled=False`

---

## Shared Patterns

### Authentication (all new backend endpoints)
**Source:** `backend/app/api/v1/filament_types.py` lines 37–40
**Apply to:** All new endpoint handlers
```python
async def my_endpoint(
    user: CurrentUser,      # validates JWT, required on all protected endpoints
    tenant: CurrentTenant,  # resolves tenant from JWT, sets RLS context
    db: TenantDB,           # session with RLS SET LOCAL, required for tenant isolation
) -> ...:
```

### Tenant Isolation (backend)
**Source:** `backend/app/api/v1/filament_types.py` lines 86–95
**Apply to:** All new SQL queries
```python
# ALWAYS scope to tenant.id — never query without this where clause
query = select(FilamentType).where(FilamentType.tenant_id == tenant.id)
# For joins with Spool: tenant_id must appear in BOTH the outerjoin condition and where clause
.outerjoin(Spool, (Spool.filament_type_id == FilamentType.id) & (Spool.tenant_id == tenant.id))
```

### Error Handling (backend)
**Source:** `backend/app/api/v1/filament_types.py` lines 140–145
**Apply to:** All new endpoints that access a specific resource by ID
```python
ft = result.scalar_one_or_none()
if not ft:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"FilamentType {filament_type_id} not found",
    )
```

### Logging (backend)
**Source:** `backend/app/api/v1/filament_types.py` lines 21, 64
**Apply to:** All new endpoint handlers
```python
logger = logging.getLogger(__name__)  # module-level
logger.info(f"Listed {len(spools)} spools for FilamentType {filament_type_id}")  # after successful ops
```

### Query Client Invalidation (frontend mutation)
**Source:** `frontend/src/components/inventory/SpoolList.tsx` lines 169–183
**Apply to:** `useToggleHasSample` mutation in `useFilamentTypes.ts`
```typescript
// Pattern: cancelQueries → optimistic update → onError rollback → onSettled invalidate
onSettled: () => {
  queryClient.invalidateQueries({ queryKey: ['filament-types'] })
},
```

### stopPropagation on nested action buttons
**Source:** `frontend/src/components/inventory/SpoolList.tsx` line 576
**Apply to:** `has_sample` toggle in `FilamentTypeCard` and `FilamentTypeRow`
```typescript
onClick={(e) => {
  e.stopPropagation()   // prevents row click from opening sheet
  onToggleSample(ft.id, !ft.has_sample)
}}
```

### Color Hex Normalization
**Source:** `frontend/src/components/inventory/SpoolCard.tsx` lines 93–96
**Apply to:** Both `FilamentTypeCard` and `FilamentTypeRow` color swatch rendering
```typescript
backgroundColor: `#${color_hex.length === 8 ? color_hex.slice(2) : color_hex}`
// 8-char hex = AARRGGBB → strip alpha prefix; 6-char = RRGGBB → use as-is
```

---

## No Analog Found

All files have close analogs in the codebase. No gaps requiring RESEARCH.md code examples as primary source.

---

## Metadata

**Analog search scope:** `frontend/src/`, `backend/app/api/v1/`, `backend/tests/`
**Files scanned:** 11 source files read directly
**Pattern extraction date:** 2026-05-20
