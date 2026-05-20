# Phase 3: Add Workflows - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 3-add-workflows
**Areas discussed:** Entry point & container, Bulk add form structure, Rapid batch flow UX, spool_id auto-generation strategy, Duplicate FilamentType handling (update), Dialog back-navigation (update)

---

## Entry Point & Container

| Option | Description | Selected |
|--------|-------------|----------|
| Header, beside Filters | [Search] [Filters] [+ Add] layout. Consistent with other list pages. | ✓ |
| Floating action button | Mobile-prominent, but new pattern not used elsewhere. | |
| Inline empty-state button only | Only visible when list is empty — awkward once populated. | |

**User's choice:** Header, beside Filters

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sheet (slide-in panel) | Consistent with Phase 2 sheet pattern. Third sheet may feel cluttered. | |
| Dialog (centered modal) | shadcn/ui Dialog. Visually distinct from browse sheets — signals action. | ✓ |
| Dedicated route (/filaments/add) | Full page. Matches existing create pages. Slower to access. | |

**User's choice:** Dialog

---

| Option | Description | Selected |
|--------|-------------|----------|
| Mode selector first | First screen lets user choose batch vs. variants. Clean mental split. | ✓ |
| Two separate Add buttons | "Add Batch" + "Add Variants" in header. More discoverable but clutters header. | |
| Always starts as rapid batch | Quantity field optional. Conflates two different workflows. | |

**User's choice:** Mode selector first

---

| Option | Description | Selected |
|--------|-------------|----------|
| Close Dialog, list refreshes | Simplest success state after bulk add. | |
| Show success summary in Dialog | Confirms IDs (FIL-011 through FIL-015) before dismissing. | |
| Stay open for rapid batch; close for bulk | Different behavior per mode. | ✓ |

**User's choice:** Stay open for rapid batch; close for bulk

---

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed max-w-lg, scrollable content | Consistent Dialog size throughout — simplest. | ✓ |
| max-w-md for selector, max-w-xl for form | Dialog grows for the full form. CSS transitions needed. | |

**User's choice:** Fixed max-w-lg, scrollable

---

## Bulk Add Form Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Core fields only + quantity | Brand/color/type + optional finish/notes + quantity. Fastest entry. | |
| All FilamentType fields + quantity | Complete form up front. Slow for bulk workflow. | |
| Core fields + expandable More options | Core fields visible; temps/diameter/density etc behind toggle. | ✓ |

**User's choice:** Core fields + expandable More options section

---

| Option | Description | Selected |
|--------|-------------|----------|
| Single weight field for all spools | "Weight per spool (g)" default 1000g. Applies to all N spools. | ✓ |
| Weight field with common presets | Dropdown: 250g / 500g / 1000g / Custom. | |
| No weight field — default 1000g always | Silent default. Creates incorrect data silently. | |

**User's choice:** Single weight field, applies to all spools

---

| Option | Description | Selected |
|--------|-------------|----------|
| One scrollable form | All fields at once. Simpler, faster for power users. | ✓ |
| Two-step wizard | Type details → Quantity & weight. Consistent with CreateRunWizard but adds overhead. | |

**User's choice:** One scrollable form

---

| Option | Description | Selected |
|--------|-------------|----------|
| 1–50 with +/− buttons | Reasonable upper bound. | |
| 1–999 | No practical upper bound. Risky. | |
| 1–20 max | Conservative. Most real batches under 20. | ✓ |

**User's choice:** 1–20 max

---

| Option | Description | Selected |
|--------|-------------|----------|
| Quantity minimum is 1 | Bulk add always creates at least one spool. | ✓ |
| Quantity can be 0 | Allows FilamentType-only creation. Adds form complexity. | |

**User's choice:** Quantity minimum is 1

---

## Rapid Batch Flow UX

| Option | Description | Selected |
|--------|-------------|----------|
| Brand + material locked; color required | Minimum fields per step. Fast but less flexible. | |
| Brand + material + diameter locked; color required | Also locks diameter. Even faster but less flexible. | |
| All fields pre-filled; user changes whatever differs | Most flexible. Higher cognitive load. | ✓ |

**User's choice:** All FilamentType fields pre-filled; user changes whatever differs

---

| Option | Description | Selected |
|--------|-------------|----------|
| Always 1 spool per step | Simple and consistent. Add same color multiple times for multiples. | ✓ |
| Quantity field per step (1–20) | Allows 3x JAYO Black PETG + 1x Red in one session. More flexible. | |

**User's choice:** Always 1 spool per step

---

| Option | Description | Selected |
|--------|-------------|----------|
| Save immediately on each step | Partial progress preserved. Simpler frontend state. | |
| Accumulate rows, then submit all | Running list of pending entries. One final submit. | ✓ |

**User's choice:** Accumulate rows, then submit all

---

| Option | Description | Selected |
|--------|-------------|----------|
| Color chips at top of Dialog | Compact [Red ✗] [Blue ✗] chips. Keeps Dialog compact. | |
| Table rows below the form | brand/color/finish per row with edit + remove. More detail. | ✓ |

**User's choice:** Table rows below the form

---

| Option | Description | Selected |
|--------|-------------|----------|
| Single weight field at top, all entries | Set once, applies to every spool. | ✓ |
| Weight field on each table row | Mixed spool sizes per batch. More complex. | |

**User's choice:** Single weight field at top

---

| Option | Description | Selected |
|--------|-------------|----------|
| Dialog stays open for another batch | Table clears, form resets, user can add another round. | ✓ |
| Dialog closes, list refreshes | Clean finish per submit. | |

**User's choice:** Dialog stays open for another batch

---

## spool_id Auto-Generation Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Backend atomically generates all N IDs in one transaction | Query max, reserve range, create all in one DB tx. | ✓ |
| Frontend calls create_spool N times sequentially | N round-trips. Race conditions. | |
| New dedicated bulk_create endpoint | Same as option 1 — clarifying it's a new endpoint. | |

**User's choice:** Backend atomically generates all N IDs in one transaction

---

| Option | Description | Selected |
|--------|-------------|----------|
| Single POST with all entries, backend generates IDs atomically | One tx, all FilamentTypes + Spools. | ✓ |
| One POST per row (N sequential API calls on submit) | Simpler backend. Complex error handling mid-loop. | |

**User's choice:** Single POST, atomic backend generation

---

| Option | Description | Selected |
|--------|-------------|----------|
| Always FIL-NNN; revisit if needed | YAGNI. Existing convention. | ✓ |
| Support tenant-level spool_id prefix | More flexible. Out of scope. | |

**User's choice:** Always FIL-NNN

---

| Option | Description | Selected |
|--------|-------------|----------|
| DB unique constraint + retry on collision | Retry once on collision. Clean failure handling. | ✓ |
| SELECT FOR UPDATE lock on max query | Correct but unnecessary lock overhead at this scale. | |
| Don't worry about it — single-user | Document assumption; no retry logic. | |

**User's choice:** DB unique constraint + retry on collision

---

## Update Session (2026-05-20) — Duplicate Handling & Back-Navigation

### Duplicate FilamentType handling

| Option | Description | Selected |
|--------|-------------|----------|
| Always create a new FilamentType | Simpler, predictable — duplicates handled manually later | |
| Reuse existing FilamentType, just add spools | Match on brand + color + material_type_id; reuse if found | ✓ |
| Return 409 Conflict with existing type's ID | Surface conflict for frontend resolution | |

**User's choice:** Reuse existing FilamentType and create spools against it

Follow-up — optional field handling on reuse:

| Option | Description | Selected |
|--------|-------------|----------|
| Ignore incoming optional fields | Keep existing record as-is | |
| Merge — fill null fields only | Existing non-null wins; null fields filled by incoming data | ✓ |
| You decide | Claude picks simpler implementation | |

**User's choice:** Merge in (existing non-null wins)

Follow-up — applies to rapid batch too:

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — same behavior for both endpoints | Each batch row checked independently | ✓ |
| No — rapid batch always creates new | Simpler per-row, could produce duplicates | |

**User's choice:** Yes — same behavior for both endpoints

---

### Dialog back-navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — back arrow at top of form | Returns to mode selector | ✓ |
| No — close and reopen Dialog | Simpler state; low friction | |

**User's choice:** Yes — back arrow

Follow-up — form state on back:

| Option | Description | Selected |
|--------|-------------|----------|
| Cleared on back | Simple; consistent with post-submit reset | |
| Preserved — state at Dialog level | Values survive mode-selector transitions | ✓ |

**User's choice:** Preserved at Dialog level

---

## Claude's Discretion

- Material type field: Select dropdown from `materialTypesApi.list()` (imported from `@/lib/api/spools`)
- Error display in Dialog: shadcn/ui `Alert` with `AlertDescription` (matches `CreateRunWizard`)
- Mode selector screen: two large clickable Cards describing each mode
- Form validation: react-hook-form + Zod, fires on submit (not on blur)
- "More options" section: shadcn/ui Collapsible, collapsed by default

## Deferred Ideas

- Configurable spool_id prefix per tenant — YAGNI
- FilamentType creation without any spools (quantity = 0) — separate feature if needed
- Mixed spool weights per rapid batch entry — single weight covers the common case
- UI for retrying a subset on submit failure — atomic guarantee means full retry only; deferred
