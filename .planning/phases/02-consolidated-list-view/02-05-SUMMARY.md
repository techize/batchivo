---
phase: 02-consolidated-list-view
plan: "05"
subsystem: frontend
tags: [react, filament-library, ui-components, mobile-desktop-split]
dependency_graph:
  requires: [02-01, 02-04]
  provides: [02-06]
  affects: [frontend/src/App.tsx]
tech_stack:
  added: []
  patterns:
    - mobile/desktop split via lg:hidden / hidden lg:block
    - optimistic toggle with stopPropagation isolation
    - stub forward-declarations for Plan 06 sheet components
key_files:
  created:
    - frontend/src/components/filaments/FilamentTypeCard.tsx
    - frontend/src/components/filaments/FilamentTypeRow.tsx
    - frontend/src/pages/FilamentLibrary.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - Used named export (FilamentLibrary) matching SpoolList convention
  - Stub components declared inline at top of FilamentLibrary.tsx (not imported) — Plan 06 replaces them
  - TooltipProvider scoped per-component (not global) to match existing badge pattern in SpoolCard
metrics:
  duration: "~8 minutes"
  completed: "2026-05-20T09:24:49Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 02 Plan 05: FilamentLibrary Page and Presentation Components Summary

FilamentLibrary page with mobile card list (FilamentTypeCard) and desktop table (FilamentTypeRow), wired into App.tsx replacing the Plan 01 stub.

## What Was Built

**FilamentTypeCard** (`frontend/src/components/filaments/FilamentTypeCard.tsx`)
- Mobile card showing brand, colour name, 12px colour swatch (conditional on color_hex), material type
- Badge row: spool count (secondary), labeled ratio (secondary/warning), sample status (success/outline)
- has_sample toggle: ghost/icon Button with TestTube2 icon, Tooltip, stopPropagation, 44px touch target
- Color hex normalization: strips `FF` alpha prefix from 8-char hex strings

**FilamentTypeRow** (`frontend/src/components/filaments/FilamentTypeRow.tsx`)
- Desktop TableRow with 7 cells: Brand / Colour (with swatch) / Material / Spools / Labels / Sample / Actions
- `cursor-pointer hover:bg-muted/50` on the row
- `tabIndex={0}` and `onKeyDown` for Enter/Space keyboard accessibility
- Actions TableCell has `onClick={(e) => e.stopPropagation()}` plus inner button stop

**FilamentLibrary** (`frontend/src/pages/FilamentLibrary.tsx`)
- State: `spoolSheetFilamentTypeId`, `spoolSheetFilamentTypeName`, `filterSheetOpen`, `params`
- Search input with live brand filter, Filters button with active-count badge
- "Needs labels" and "No sample" quick-filter toggles with `aria-pressed`
- Loading (spinner + text), Error (destructive/10 bg + retry button), Empty (two variants: filters/no-data)
- `lg:hidden` mobile cards, `hidden lg:block` desktop table with proper header columns
- FilamentTypeSpoolSheet + FilamentTypeFilterSheet stubbed with `(_props: any) => null` pending Plan 06

**App.tsx** — inline stub replaced with `import { FilamentLibrary } from '@/pages/FilamentLibrary'`

## Verification

- `pnpm tsc --noEmit` exits 0
- "Filament Library" heading present in JSX
- Both `lg:hidden` and `hidden lg:block` breakpoint classes present
- `stopPropagation` present in both FilamentTypeCard and FilamentTypeRow
- App.tsx imports from `@/pages/FilamentLibrary` (not inline stub)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `FilamentTypeSpoolSheet = (_props: any) => null` | FilamentLibrary.tsx | ~18 | Plan 06 creates the real component |
| `FilamentTypeFilterSheet = (_props: any) => null` | FilamentLibrary.tsx | ~21 | Plan 06 creates the real component |

These stubs are intentional — Plan 06 replaces them with real sheet components.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced. All rendered data is tenant-scoped at the API layer (Plan 04). React JSX escapes text nodes by default — no innerHTML usage.

## Self-Check: PASSED

- `/Users/jonathan/Repos/batchivo/frontend/src/components/filaments/FilamentTypeCard.tsx` — FOUND
- `/Users/jonathan/Repos/batchivo/frontend/src/components/filaments/FilamentTypeRow.tsx` — FOUND
- `/Users/jonathan/Repos/batchivo/frontend/src/pages/FilamentLibrary.tsx` — FOUND
- Commit `6d43a9f` — FOUND
