# Phase 3: Add Workflows - Research

**Researched:** 2026-05-20
**Domain:** FastAPI bulk/batch endpoints + React Dialog-based form workflows with accumulated state
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Entry Point & Container**
- D-01: "+ Add" button in FilamentLibrary page header, beside Filters button. Layout: `[Search] [Filters] [+ Add]`.
- D-02: Clicking opens a shadcn/ui Dialog, `max-w-lg`, scrollable content. No size transition between mode selector and form.
- D-03: First screen = mode selector: "Add a batch of identical spools" vs "Add multiple color variants".
- D-04: After bulk add succeeds, Dialog closes and list refreshes.
- D-05: After rapid batch submit succeeds, Dialog stays open, table clears, form resets to last-used values.

**Back Navigation**
- D-22: Both forms show a back button (ArrowLeft icon) returning to mode selector. No one-way flow.
- D-23: Form state is preserved on back navigation. State held at Dialog level, not inside mode-specific sub-components.

**Bulk Add Form**
- D-06: Single scrollable form — no wizard steps.
- D-07: Fields: brand, color, material type, finish, notes (visible) + "More options" collapsible for color_hex, diameter, extruder_temp, bed_temp, density, pattern, translucent, glow, spool_type.
- D-08: Quantity: numeric input with +/− buttons, range 1–20.
- D-09: Weight per spool: single field (default 1000g).

**Rapid Batch Add Form**
- D-10: Shared weight field at top (default 1000g), applies to every spool in the batch.
- D-11: Each color step shows all FilamentType fields pre-filled from previous entry; only color is semantically required per step.
- D-12: Each step creates 1 spool. No per-step quantity field.
- D-13: "Add color" appends to accumulator table (columns: brand, color, material type, finish, remove button). Nothing sent to backend until "Submit all".
- D-14: After "Submit all" succeeds: Dialog stays open, table clears, form resets to last-used values.

**Backend Duplicate Handling**
- D-19: Both endpoints check for existing FilamentType matching `(tenant_id, brand, color, material_type_id)` before inserting.
- D-20: If match found, reuse existing FilamentType. Optional fields merged in: existing non-null wins; null fields on existing record are filled by incoming data.
- D-21: Match-and-reuse applies identically to both endpoints. For batch-create, each row checked independently.

**Backend API Design**
- D-15: Two new endpoints:
  - `POST /api/v1/filament-types/bulk-create`
  - `POST /api/v1/filament-types/batch-create`
- D-16: Spool IDs generated atomically server-side: query `MAX(spool_id LIKE 'FIL-%')` within the same transaction.
- D-17: spool_id format always `FIL-NNN` (zero-padded 3+ digits).
- D-18: Collision handling: UNIQUE constraint on `(tenant_id, spool_id)`. Retry once on 409; return HTTP 409 after second failure.

**Claude's Discretion (all locked for this research)**
- Material type field: `Select` dropdown populated from `materialTypesApi.list()` (import from `@/lib/api/spools`).
- Error display: shadcn/ui `Alert` with `AlertDescription`, same as `CreateRunWizard`.
- Mode selector: two large clickable Cards.
- Form validation: `react-hook-form` + Zod, fires on submit (not blur).

### Deferred Ideas (OUT OF SCOPE)
- Configurable spool_id prefix per tenant
- FilamentType creation without any spools (quantity = 0)
- Mixed spool weights per rapid batch entry
- UI for partial failure in "Submit all" (atomic = full retry only)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADD-01 | User can add a new FilamentType and specify a quantity; system auto-generates that many Spool records with sequential spool IDs | D-15 bulk-create endpoint + D-16 atomic spool ID generation |
| ADD-02 | Auto-generated spool IDs follow the existing `FIL-NNN` convention | D-17 format spec + existing `duplicate_spool` helper to extract |
| ADD-03 | After bulk add, newly created spools appear in the list as "needs label" with clear visual indicator | Spool.is_labeled defaults False; query invalidation triggers list refresh; Badge component available |
| ADD-04 | User can enter a brand and material type once, then step through adding multiple color variants with those fields pre-filled | D-11 pre-fill from previous entry + accumulator table pattern |
| ADD-05 | Each step in the rapid batch flow requires only color (and optionally finish/notes) to create a new FilamentType + initial spool | D-12 one spool per step; Zod schema makes only color required per entry row |
</phase_requirements>

---

## Summary

Phase 3 adds two add-filament workflows behind a single Dialog entry point in the FilamentLibrary page header. All design decisions are locked in CONTEXT.md; research here focuses on verifying implementation mechanics, surfacing pitfalls, and providing code-level patterns the planner can act on directly.

The backend work is well-defined: two new endpoints on the existing `filament_types.py` router, each performing find-or-create of a FilamentType and then bulk-inserting Spools in a single SQLAlchemy transaction. The key implementation detail is the atomic spool ID reservation — a helper extracted from the existing `duplicate_spool` logic in `spools.py` that queries `MAX(spool_id LIKE 'FIL-%')` and reserves N IDs in the same transaction before committing.

The frontend work follows established patterns: a shadcn/ui Dialog with a three-screen state machine (`selector | bulk | batch`), react-hook-form + Zod on both forms, and TanStack Query mutations for both endpoints. The rapid batch form has one unusual pattern — an accumulator table (rows held in component state, submitted in one mutation call) — which has a direct reference implementation in `CreateRunWizard.tsx`.

**Primary recommendation:** Extract `_next_spool_ids(db, tenant_id, count)` from `spools.py:duplicate_spool` first (it is the shared primitive both endpoints depend on), then build `bulk-create` and `batch-create` on top of it before touching the frontend.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FilamentType find-or-create logic | API / Backend | — | Duplicate detection needs DB access; cannot be client-side |
| Atomic spool ID reservation | API / Backend | — | Race-condition safety requires a DB-level lock within the transaction |
| Spool bulk insert (N spools) | API / Backend | — | Single atomic transaction is a backend concern |
| Dialog state machine (mode/bulk/batch) | Frontend SPA | — | Local UI state; no persistence needed |
| Accumulator table rows (rapid batch) | Frontend SPA | — | Local state until "Submit all" |
| Form state preservation across back navigation | Frontend SPA | — | Held at Dialog component level per D-23 |
| Query invalidation after success | Frontend SPA | — | TanStack Query `invalidateQueries(['filament-types'])` |
| "Needs label" indicator on newly added spools | Frontend SPA + API | — | `is_labeled=False` set by backend; badge rendered by existing FilamentTypeRow/Card |

---

## Standard Stack

### Core

No new packages required. Phase 3 uses the stack already in the project.

| Library | Verified Version | Purpose | Status |
|---------|-----------------|---------|--------|
| FastAPI | >=0.124.4 (pinned) | API endpoints | Already installed |
| SQLAlchemy 2.0 async | pinned | Async ORM, `AsyncSession` | Already installed |
| react-hook-form | 7.x | Form state, validation wiring | Already installed |
| Zod 4.x | pinned | Schema validation | Already installed |
| TanStack Query | 5.90 | Mutations + query invalidation | Already installed |
| shadcn/ui Dialog | already in `components/ui/` | Add workflow container | Already installed |
| shadcn/ui Collapsible | already in `components/ui/` | "More options" section | Already installed |

[VERIFIED: codebase grep] All components listed in the UI-SPEC `## Component Inventory` table are confirmed present in `frontend/src/components/ui/`.

### No Package Legitimacy Audit Needed

Zero new packages are installed in this phase. All required components (Dialog, Collapsible, Form, Table, Alert, Badge, Select, Card) are already present in `frontend/src/components/ui/`. [VERIFIED: codebase `ls frontend/src/components/ui/`]

---

## Architecture Patterns

### System Architecture: Add Workflow Data Flow

```
FilamentLibrary (page)
  └─ "+ Add Filament" button click
       └─ AddFilamentDialog (new component, Dialog container)
            ├─ Screen: ModeSelector
            │    ├─ Card: "Batch identical spools" → mode='bulk'
            │    └─ Card: "Color variants" → mode='batch'
            ├─ Screen: BulkAddForm (react-hook-form + Zod)
            │    └─ Submit → POST /api/v1/filament-types/bulk-create
            │         └─ success → close Dialog → invalidate ['filament-types']
            └─ Screen: RapidBatchForm (react-hook-form + Zod + rows state)
                 ├─ "Add color" → append row to local state
                 └─ "Submit all" → POST /api/v1/filament-types/batch-create
                      └─ success → clear table, reset form to last values

Backend: POST /api/v1/filament-types/bulk-create
  ├─ find-or-create FilamentType (brand+color+material_type_id match)
  └─ _next_spool_ids(db, tenant_id, N) → reserve FIL-NNN range atomically
       └─ bulk INSERT N Spool records (is_labeled=False)
            └─ return FilamentTypeResponse + list[spool_id]

Backend: POST /api/v1/filament-types/batch-create
  ├─ for each entry: find-or-create FilamentType
  └─ _next_spool_ids(db, tenant_id, len(entries)) → reserve range
       └─ bulk INSERT one Spool per entry (is_labeled=False)
            └─ return list[{filament_type, spool_id}]
```

### Recommended Project Structure (new files only)

```
backend/app/api/v1/
├─ filament_types.py          # existing — add bulk_create + batch_create + _next_spool_ids helper

frontend/src/
├─ components/filaments/
│   └─ AddFilamentDialog.tsx  # new — Dialog container + state machine
├─ lib/api/
│   └─ filament-types.ts      # existing — add bulkCreate + batchCreate methods
├─ hooks/
│   └─ useFilamentTypes.ts    # existing — add useBulkCreateFilamentType + useBatchCreateFilamentTypes
├─ types/
│   └─ filament-type.ts       # existing — add BulkCreateRequest, BatchCreateRequest, BulkCreateResponse, BatchCreateResponse
└─ pages/
    └─ FilamentLibrary.tsx     # existing — add Dialog open state + button
```

**Note on component decomposition:** The CONTEXT.md and UI-SPEC both describe the Dialog as a single container. For simplicity and to avoid prop-drilling the back-navigation state, the entire Dialog (all three screens) can live in a single `AddFilamentDialog.tsx` component with internal `mode` state. Sub-sections can be extracted to inline helper components or separate files if `AddFilamentDialog.tsx` grows beyond ~250 lines.

### Pattern 1: Atomic Spool ID Reservation (Backend)

**What:** Extract the FIL-NNN generation from `duplicate_spool` into a reusable helper that reserves N sequential IDs within a transaction.

**When to use:** Any endpoint that needs to create multiple spools in one request.

```python
# Source: backend/app/api/v1/spools.py ~L404 (existing logic, generalised)
async def _next_spool_ids(db: AsyncSession, tenant_id: UUID, count: int) -> list[str]:
    """
    Reserve `count` sequential FIL-NNN spool IDs for a tenant.
    Must be called within an open transaction (caller's async with db.begin() block).
    """
    max_query = select(func.max(Spool.spool_id)).where(
        Spool.tenant_id == tenant_id,
        Spool.spool_id.like("FIL-%"),
    )
    max_result = await db.execute(max_query)
    max_spool_id = max_result.scalar_one_or_none()

    if max_spool_id:
        try:
            current_num = int(max_spool_id.replace("FIL-", ""))
        except ValueError:
            current_num = 0
    else:
        current_num = 0

    return [f"FIL-{current_num + i + 1:03d}" for i in range(count)]
```

[CITED: backend/app/api/v1/spools.py:L404-L419]

**Collision handling:** The `UNIQUE` constraint on `(tenant_id, spool_id)` is the safety net. If two requests race and both reserve the same range, one will hit IntegrityError on commit. Catch `IntegrityError`, rollback, call `_next_spool_ids` again, retry once. Return HTTP 409 after second failure.

### Pattern 2: Find-or-Create FilamentType (Backend)

**What:** Lookup by `(tenant_id, brand, color, material_type_id)` before inserting. If found, merge optional fields (existing non-null wins).

```python
# Source: CONTEXT.md D-19, D-20
async def _find_or_create_filament_type(
    db: AsyncSession,
    tenant_id: UUID,
    data: FilamentTypeCreate,
) -> FilamentType:
    result = await db.execute(
        select(FilamentType).where(
            FilamentType.tenant_id == tenant_id,
            FilamentType.brand == data.brand,
            FilamentType.color == data.color,
            FilamentType.material_type_id == data.material_type_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Merge optional fields: null on existing record filled by incoming
        incoming = data.model_dump(exclude_unset=False)
        optional_fields = ['color_hex', 'finish', 'pattern', 'spool_type', 'notes',
                           'density', 'extruder_temp', 'bed_temp']
        changed = False
        for field in optional_fields:
            if getattr(existing, field) is None and incoming.get(field) is not None:
                setattr(existing, field, incoming[field])
                changed = True
        if changed:
            db.add(existing)
        return existing

    ft = FilamentType(tenant_id=tenant_id, **data.model_dump())
    db.add(ft)
    await db.flush()  # get ID without committing
    await db.refresh(ft)
    return ft
```

[CITED: CONTEXT.md D-19, D-20, D-21]

**Note:** Use `db.flush()` (not `db.commit()`) inside a larger transaction to get the ID while keeping everything atomic.

### Pattern 3: Atomic Bulk Transaction (Backend)

**What:** All spool creation must commit in one transaction. Use `begin_nested()` or a `try/except IntegrityError` wrapping the entire operation.

```python
# Source: established pattern in backend/app/api/v1/ — all multi-record creates
@router.post("/bulk-create", response_model=BulkCreateResponse, status_code=201)
async def bulk_create(
    data: BulkCreateRequest,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> BulkCreateResponse:
    try:
        ft = await _find_or_create_filament_type(db, tenant.id, data)
        spool_ids = await _next_spool_ids(db, tenant.id, data.quantity)
        spools = [
            Spool(
                tenant_id=tenant.id,
                filament_type_id=ft.id,
                spool_id=sid,
                initial_weight=data.initial_weight,
                current_weight=data.initial_weight,
                is_labeled=False,
                is_active=True,
            )
            for sid in spool_ids
        ]
        db.add_all(spools)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Retry once (race condition on spool_id uniqueness)
        ...  # retry logic here
    ...
```

[CITED: CONTEXT.md D-16, D-18; existing IntegrityError pattern in filament_types.py]

### Pattern 4: Dialog State Machine (Frontend)

**What:** Three-screen state machine held in `AddFilamentDialog` component. Form state (bulk and batch) held at Dialog level so back navigation preserves it (D-23).

```typescript
// Source: CONTEXT.md D-22, D-23; CreateRunWizard.tsx pattern
type DialogMode = 'selector' | 'bulk' | 'batch'

export function AddFilamentDialog() {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<DialogMode>('selector')

  // Held at Dialog level — survives mode transitions
  const bulkForm = useForm<BulkAddFormValues>({ ... })
  const batchForm = useForm<BatchEntryFormValues>({ ... })
  const [batchRows, setBatchRows] = useState<BatchRowEntry[]>([])

  const handleClose = () => {
    setOpen(false)
    setMode('selector')  // reset on close, but NOT on back — D-23
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg overflow-y-auto max-h-[90vh]">
        {mode === 'selector' && <ModeSelector onSelect={setMode} />}
        {mode === 'bulk'     && <BulkAddForm form={bulkForm} onBack={() => setMode('selector')} ... />}
        {mode === 'batch'    && <RapidBatchForm form={batchForm} rows={batchRows} ... />}
      </DialogContent>
    </Dialog>
  )
}
```

[CITED: CONTEXT.md D-03, D-22, D-23; frontend/src/components/production-runs/CreateRunWizard.tsx]

### Pattern 5: Accumulator Table with Mutation (Frontend — Rapid Batch)

**What:** Local `rows` state accumulates entries; "Submit all" fires a single `useMutation` with the entire array. After success, clear rows and reset form to last-used values (D-14).

```typescript
// Source: CreateRunWizard.tsx pattern (items accumulation)
const batchMutation = useBatchCreateFilamentTypes()

const handleAddColor = (entry: BatchRowEntry) => {
  setBatchRows(prev => [...prev, entry])
  // Pre-fill next form entry from this one (D-11)
  batchForm.reset({ ...entry, color: '' })
}

const handleSubmitAll = async () => {
  const lastEntry = batchRows[batchRows.length - 1]
  await batchMutation.mutateAsync({ entries: batchRows, initial_weight: sharedWeight })
  setBatchRows([])
  if (lastEntry) batchForm.reset({ ...lastEntry, color: '' })
}
```

[CITED: CONTEXT.md D-11, D-13, D-14; CreateRunWizard.tsx]

### Pattern 6: API Client Methods (Frontend)

**What:** Add `bulkCreate` and `batchCreate` to `frontend/src/lib/api/filament-types.ts`.

```typescript
// Source: existing filament-types.ts pattern
bulkCreate: async (data: BulkCreateRequest): Promise<BulkCreateResponse> => {
  return apiClient.post<BulkCreateResponse>('/api/v1/filament-types/bulk-create', data)
},

batchCreate: async (data: BatchCreateRequest): Promise<BatchCreateResponse> => {
  return apiClient.post<BatchCreateResponse>('/api/v1/filament-types/batch-create', data)
},
```

[CITED: frontend/src/lib/api/filament-types.ts existing structure]

### Pattern 7: Mutation Hooks (Frontend)

**What:** Two new hooks in `useFilamentTypes.ts`, following the established `useMutation` + `invalidateQueries` pattern.

```typescript
// Source: useFilamentTypes.ts — useToggleHasSample pattern
export function useBulkCreateFilamentType() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: filamentTypesApi.bulkCreate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['filament-types'] })
    },
  })
}

export function useBatchCreateFilamentTypes() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: filamentTypesApi.batchCreate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['filament-types'] })
    },
  })
}
```

[CITED: frontend/src/hooks/useFilamentTypes.ts:L43-89]

### Anti-Patterns to Avoid

- **Committing inside `_find_or_create_filament_type`:** This breaks atomicity. Use `db.flush()` to get the ID without committing. The outer endpoint handler commits once at the end.
- **Sequential spool ID generation (one at a time):** The existing `duplicate_spool` code works for N=1. For N>1, query the MAX once and generate the full range — do not loop with individual SELECTs or you will have O(N) queries and potential race conditions.
- **Calling `_next_spool_ids` outside an open transaction:** The IDs are reserved optimistically by the MAX query; they are only safe if the INSERT immediately follows in the same transaction before any other request can grab the same range.
- **Holding form state inside mode-specific sub-components:** D-23 explicitly requires state at the Dialog level. If bulk/batch form state lives inside `BulkAddForm`/`RapidBatchForm` as local `useForm` calls, it will be lost when switching modes.
- **Re-using the same queryKey for mutation responses:** After `bulkCreate`, invalidate `['filament-types']` — not a narrower key — because the aggregated list counts change for potentially existing FilamentTypes.
- **Calling `batchForm.reset({})` on success (rapid batch):** D-14 says reset to last-used values, not empty. Capture the last entry before clearing rows and pass it as the reset argument.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom field validators | `react-hook-form` + Zod schema | Type-safe, handles nested errors, already in project |
| Optimistic updates / loading state | Manual `isSubmitting` booleans | `mutation.isPending` from `useMutation` | Race-condition safe, built into TanStack Query |
| Material type dropdown | Fetch in AddFilamentDialog | `materialTypesApi.list()` with `useQuery` (pattern from FilterSheet) | Already cached in `['material-types']` key — no duplicate fetches |
| Sequential spool ID lock | Custom locking table | `UNIQUE` constraint + single-transaction MAX query | DB uniqueness constraint is the authoritative lock |
| Dialog scroll/overflow | Custom scroll container | `overflow-y-auto max-h-[90vh]` on `DialogContent` | CSS is sufficient; shadcn/ui Dialog renders in a portal |

---

## Common Pitfalls

### Pitfall 1: `db.commit()` Inside Helper Called Within a Transaction

**What goes wrong:** If `_find_or_create_filament_type` calls `await db.commit()` internally, and the spool insert later fails, the FilamentType is already committed and cannot be rolled back.

**Why it happens:** SQLAlchemy async sessions allow commit anywhere, but it breaks the atomicity guarantee.

**How to avoid:** Helper functions that are part of a larger atomic operation must use `db.flush()` only. The endpoint handler owns the single `await db.commit()` call.

**Warning signs:** FilamentTypes appearing in the database without any child Spools.

### Pitfall 2: Race Condition on Spool ID Reservation

**What goes wrong:** Two concurrent `bulk-create` requests both query MAX = "FIL-042", both try to insert FIL-043. One hits IntegrityError on commit.

**Why it happens:** The MAX query and INSERT are not atomic unless wrapped in a SERIALIZABLE transaction or a unique index catch.

**How to avoid:** The `UNIQUE` constraint on `(tenant_id, spool_id)` is the safety net — IntegrityError is expected. Catch it, rollback, retry once. This is already the documented behavior (D-18).

**Warning signs:** HTTP 409 responses on the first submission (not a retry) — indicates the constraint is working but retry logic is missing.

### Pitfall 3: Static Routes Must Precede Dynamic Routes

**What goes wrong:** FastAPI matches `bulk-create` as a UUID value for `/{filament_type_id}` if the static route is registered after the dynamic one.

**Why it happens:** FastAPI route ordering is registration order within the router.

**How to avoid:** Register `bulk-create` and `batch-create` at the top of the router file, before the `/{filament_type_id}` GET/PUT/DELETE routes. Confirmed issue from STATE.md: "Static paths must precede dynamic to avoid FastAPI matching literal strings as UUIDs."

[CITED: .planning/STATE.md Accumulated Context — Decisions]

**Warning signs:** HTTP 422 or 404 on `POST /api/v1/filament-types/bulk-create` when the `/{filament_type_id}` route exists.

### Pitfall 4: `material_type_id` Required but Missing from Zod Schema

**What goes wrong:** The Zod schema omits `material_type_id` validation, allowing empty selects through to the backend, which returns 422.

**Why it happens:** shadcn/ui `Select` returns empty string `""` (not `undefined`) when nothing is selected. Zod `z.string().uuid()` fails for empty string but the error message is confusing without explicit validation.

**How to avoid:** Use `z.string().min(1, 'Material type is required')` — or validate it is a valid UUID format. The select default value should be `""` and the Zod schema should reject it explicitly.

### Pitfall 5: `batchRows` State Not Preserved When Dialog Closes Mid-session

**What goes wrong:** User starts a rapid batch session, navigates away (another page), comes back — the rows are gone because component state was unmounted.

**Why it happens:** React state is unmounted when the component unmounts (Dialog closes fully).

**How to avoid:** This is acceptable behavior per D-14 (Dialog stays open after submit success). The Dialog only closes explicitly when the user clicks Close or the X button. Documenting this so the planner does not add persistence logic for this case.

### Pitfall 6: `color_hex` Validation — Backend vs Frontend Mismatch

**What goes wrong:** The backend FilamentType model accepts `color_hex` as a raw hex string (e.g., `FF5733`), but the UI-SPEC Zod schema uses `^#[0-9a-fA-F]{6}$` (with `#` prefix).

**Why it happens:** The FilamentType schema `String(9)` accommodates RGBA (`00FF5733`), but the UI only provides standard RGB hex with a `#` prefix.

**How to avoid:** Strip the leading `#` before sending to the backend, or confirm the backend accepts `#FF5733`. Check: `backend/app/schemas/filament_type.py` does not validate the `#` prefix (field is `max_length=9`). Strip `#` in the API client before POST.

[CITED: backend/app/schemas/filament_type.py:L16; frontend/src/pages/03-UI-SPEC.md — Form Validation Contract]

---

## Code Examples

### New Pydantic Schemas Required

```python
# Source: CONTEXT.md D-15; existing FilamentTypeCreate pattern
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class BulkCreateRequest(BaseModel):
    # FilamentType fields
    material_type_id: UUID
    brand: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=9)
    finish: Optional[str] = Field(None, max_length=50)
    pattern: Optional[str] = Field(None, max_length=50)
    spool_type: Optional[str] = Field(None, max_length=50)
    diameter: float = Field(1.75, gt=0, le=5)
    density: Optional[float] = None
    extruder_temp: Optional[int] = None
    bed_temp: Optional[int] = None
    translucent: bool = False
    glow: bool = False
    notes: Optional[str] = None
    # Spool fields
    quantity: int = Field(..., ge=1, le=20)
    initial_weight: float = Field(1000.0, gt=0)

class BulkCreateResponse(BaseModel):
    filament_type_id: UUID
    spool_ids: list[str]

class BatchEntryRequest(BaseModel):
    material_type_id: UUID
    brand: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=50)
    color_hex: Optional[str] = None
    finish: Optional[str] = None
    pattern: Optional[str] = None
    spool_type: Optional[str] = None
    diameter: float = 1.75
    density: Optional[float] = None
    extruder_temp: Optional[int] = None
    bed_temp: Optional[int] = None
    translucent: bool = False
    glow: bool = False
    notes: Optional[str] = None

class BatchCreateRequest(BaseModel):
    entries: list[BatchEntryRequest] = Field(..., min_length=1)
    initial_weight: float = Field(1000.0, gt=0)

class BatchCreateResponse(BaseModel):
    results: list[dict]  # [{filament_type_id, spool_id}]
```

[CITED: CONTEXT.md D-15; backend/app/schemas/filament_type.py]

### TypeScript Types Required

```typescript
// Source: CONTEXT.md D-15; existing filament-type.ts pattern
export interface BulkCreateRequest {
  material_type_id: string
  brand: string
  color: string
  color_hex?: string | null
  finish?: string | null
  pattern?: string | null
  spool_type?: string | null
  diameter?: number
  density?: number | null
  extruder_temp?: number | null
  bed_temp?: number | null
  translucent?: boolean
  glow?: boolean
  notes?: string | null
  quantity: number
  initial_weight: number
}

export interface BulkCreateResponse {
  filament_type_id: string
  spool_ids: string[]
}

export interface BatchEntryRequest {
  material_type_id: string
  brand: string
  color: string
  color_hex?: string | null
  finish?: string | null
  // ... same optional fields as BulkCreateRequest minus quantity/initial_weight
}

export interface BatchCreateRequest {
  entries: BatchEntryRequest[]
  initial_weight: number
}

export interface BatchCreateResponse {
  results: Array<{ filament_type_id: string; spool_id: string }>
}
```

[CITED: frontend/src/types/filament-type.ts existing pattern]

---

## State of the Art

| Old Approach | Current Approach | Impact for Phase 3 |
|--------------|------------------|---------------------|
| Single spools.py with all filament logic | Two-tier: `filament_types.py` + `spools.py` | New endpoints go in `filament_types.py`; spool ID helper extracted from `spools.py` |
| Spool creation with duplicated type fields | FilamentType FK on Spool | bulk-create/batch-create create the type first, then attach spools to it |
| `/inventory` route | `/filaments` route (Phase 2 complete) | No route changes needed in Phase 3 |

---

## Assumptions Log

> All claims were verified against the codebase or explicitly cited from CONTEXT.md. No assumptions requiring user confirmation.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `color_hex` backend expects no `#` prefix (max_length=9 allows RGBA without `#`) | Pitfall 6 | Frontend must strip `#` before POST; if backend accepts `#`, strip is harmless |

---

## Open Questions (RESOLVED)

1. **`color_hex` prefix handling (A1)**
   - What we know: Backend `String(9)` field; RGBA is 8 chars without `#` or 9 chars with it; UI-SPEC Zod regex uses `^#[0-9a-fA-F]{6}$`
   - What's unclear: Does the backend/existing data expect `#FF5733` or `FF5733`?
   - Recommendation: Strip `#` in the API client before sending. This is backward compatible with either convention and the existing `FilamentTypeAggregatedResponse` does not include `color_hex`, so no migration concern.
   - **RESOLVED:** Strip `#` in the API client (filament-types.ts) before POST — backward-compatible with either backend convention per Pitfall 6.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Backend API | ✓ | 3.14.4 | — |
| Poetry | Backend dependency management | ✓ | 2.4.1 | — |
| Node.js | Frontend build | ✓ | v25.9.0 | — |
| pnpm | Frontend package manager | ✗ | — | npm (package-lock.json present) |
| PostgreSQL | Integration tests | [ASSUMED] | — | SQLite for unit tests (conftest.py fallback) |

**pnpm not found locally:** `pnpm-lock.yaml` is the canonical lockfile per CLAUDE.md. CI will use pnpm. Local development can fall back to `npm install` with the `package-lock.json` present, but `pnpm install` is preferred.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && poetry run pytest tests/integration/test_filament_types_api.py -x` |
| Full suite command | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| Frontend unit tests | `cd frontend && npm run test` (Vitest) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADD-01 | `POST /bulk-create` returns 201, creates FilamentType + N Spools | integration | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate -x` | ❌ Wave 0 |
| ADD-01 | Quantity 1 creates 1 spool; quantity 5 creates 5 spools | integration | same | ❌ Wave 0 |
| ADD-01 | Requires auth (401 without token) | integration | same | ❌ Wave 0 |
| ADD-02 | Spool IDs follow `FIL-NNN` format, sequential from current max | integration | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate::test_spool_id_format -x` | ❌ Wave 0 |
| ADD-02 | Atomic reservation — no gaps in IDs after bulk create | integration | same | ❌ Wave 0 |
| ADD-03 | All created spools have `is_labeled=False` | integration | same | ❌ Wave 0 |
| ADD-04 | `POST /batch-create` creates N FilamentTypes + N Spools atomically | integration | `pytest tests/integration/test_filament_types_api.py::TestBatchCreate -x` | ❌ Wave 0 |
| ADD-04 | Duplicate handling — reuses existing FilamentType for matching brand+color+material | integration | same | ❌ Wave 0 |
| ADD-05 | Batch entry with only color (brand+material pre-supplied) creates valid records | integration | same | ❌ Wave 0 |
| D-18 | HTTP 409 returned on spool ID collision (simulated) | integration | unit-level with mock | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && poetry run pytest tests/integration/test_filament_types_api.py -x`
- **Per wave merge:** `cd backend && poetry run pytest --cov=app --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/integration/test_filament_types_api.py` — add `TestBulkCreate` and `TestBatchCreate` test classes (file exists, classes don't)
- [ ] Fixtures: `test_filament_type` and `test_spool` already exist in `conftest.py`; no new fixtures needed for basic tests
- [ ] Frontend: `frontend/src/components/filaments/AddFilamentDialog.test.tsx` — covers Dialog state machine, form submission, query invalidation

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `CurrentUser` dependency (JWT) — required on both new endpoints |
| V3 Session Management | no | Handled globally |
| V4 Access Control | yes | `CurrentTenant` dependency + RLS via `TenantDB` — mandatory on both endpoints |
| V5 Input Validation | yes | Pydantic schemas with field constraints (quantity 1–20, initial_weight > 0) |
| V6 Cryptography | no | No crypto operations in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-tenant spool creation | Elevation of Privilege | `tenant_id` injected from JWT, never from request body; `CurrentTenant` dependency |
| Unbounded bulk insert (quantity > 20) | Denial of Service | Pydantic `Field(ge=1, le=20)` on quantity; validated before DB write |
| Empty batch-create (0 entries) | DoS / data integrity | Pydantic `Field(min_length=1)` on `entries` list |
| Spool ID injection (client-supplied IDs) | Tampering | IDs are entirely server-generated; request bodies carry no `spool_id` field |

---

## Sources

### Primary (HIGH confidence — codebase verified)

- `backend/app/api/v1/filament_types.py` — existing endpoint structure, IntegrityError handling pattern
- `backend/app/api/v1/spools.py:L370-441` — `duplicate_spool` with FIL-NNN generation logic to extract
- `backend/app/models/filament_type.py` — all FilamentType fields, constraints
- `backend/app/models/spool.py` — Spool model, `is_labeled` field
- `backend/app/schemas/filament_type.py` — Pydantic schema hierarchy
- `backend/app/modules/threed_print/filament_types.py` — `FilamentTypesModule.register_routes()` pattern
- `backend/tests/conftest.py` — available fixtures: `test_material_type`, `test_filament_type`, `test_spool`
- `frontend/src/pages/FilamentLibrary.tsx` — header layout to extend with Add button
- `frontend/src/hooks/useFilamentTypes.ts` — mutation hook pattern
- `frontend/src/lib/api/filament-types.ts` — API client pattern
- `frontend/src/types/filament-type.ts` — TypeScript type definitions
- `frontend/src/components/filaments/FilamentTypeFilterSheet.tsx` — `materialTypesApi.list()` usage
- `frontend/src/components/production-runs/CreateRunWizard.tsx` — accumulator table + multi-screen Dialog pattern
- `.planning/phases/03-add-workflows/03-CONTEXT.md` — all locked decisions
- `.planning/phases/03-add-workflows/03-UI-SPEC.md` — UI contract, component inventory, Zod schemas
- `.planning/STATE.md` — "static paths before dynamic" warning

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — ADD-01 through ADD-05 requirement text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified as already installed in codebase
- Architecture: HIGH — patterns verified against existing working code in the same repo
- Pitfalls: HIGH — two pitfalls (static route ordering, `db.flush` vs `db.commit`) directly confirmed by STATE.md and existing code patterns
- Test plan: HIGH — test framework confirmed operational, fixture availability confirmed

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (stable stack, no fast-moving dependencies in this phase)
