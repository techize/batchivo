---
phase: 02-consolidated-list-view
plan: "01"
subsystem: frontend-routing
tags: [routing, navigation, redirect]
dependency_graph:
  requires: []
  provides: [inventory-redirect, filaments-canonical-route, nav-deduplication]
  affects: [frontend/src/App.tsx, frontend/src/components/layout/AppLayout.tsx, backend/app/api/v1/modules.py]
tech_stack:
  added: []
  patterns: [TanStack Router Navigate redirect, stub component placeholder]
key_files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/layout/AppLayout.tsx
    - backend/app/api/v1/modules.py
    - frontend/src/components/dashboard/LowStockAlerts.tsx
decisions:
  - inventoryRoute renders Navigate only (no auth gating) — redirect does not expose protected content; /filaments itself is protected
  - FilamentLibrary stub defined inline in App.tsx; real component deferred to Plan 05
  - LowStockAlerts /inventory link updated to /filaments as Rule 1 auto-fix (pre-existing nav link to deprecated route)
metrics:
  duration: ~5 minutes
  completed: 2026-05-20
---

# Phase 02 Plan 01: Nav Routing Summary

**One-liner:** inventoryRoute redirects to /filaments via Navigate; MODULE_NAVIGATION and fallbackNavItems consolidated to single /filaments entry; stale LowStockAlerts nav link fixed.

**Status:** Complete
**Wave:** 1

## What Was Done

- `frontend/src/App.tsx`: inventoryRoute now renders `<Navigate to="/filaments" />` with no auth wrapper; filamentsRoute uses FilamentLibrary stub inside ProtectedRoute+ModuleGuard
- `frontend/src/components/layout/AppLayout.tsx`: removed /inventory entry from fallbackNavItems array
- `backend/app/api/v1/modules.py`: MODULE_NAVIGATION["spools"] consolidated to single /filaments entry
- `frontend/src/components/dashboard/LowStockAlerts.tsx`: updated stale `/inventory` Link to `/filaments` (Rule 1 auto-fix)

## Verification Results

- TypeScript compiles with no errors (`tsc --noEmit` exits 0)
- ruff check passes on modules.py
- No /inventory references remain in any navigation context across frontend/src/
- inventoryRoute remains registered in routeTree.addChildren([...])

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale /inventory link in LowStockAlerts.tsx**
- **Found during:** Final verification grep (`grep -rn '"/inventory"' frontend/src/`)
- **Issue:** `LowStockAlerts.tsx` line 111 had `<Link to="/inventory">View Inventory</Link>` — an internal nav link to the deprecated route, violating NAV-02
- **Fix:** Updated to `<Link to="/filaments">View Inventory</Link>`
- **Files modified:** `frontend/src/components/dashboard/LowStockAlerts.tsx`
- **Commit:** ddd2794

## Artifacts

- `frontend/src/App.tsx` — inventory redirect; filaments route with FilamentLibrary stub
- `frontend/src/components/layout/AppLayout.tsx` — /inventory removed from fallback nav
- `backend/app/api/v1/modules.py` — single /filaments nav entry in MODULE_NAVIGATION["spools"]
- `frontend/src/components/dashboard/LowStockAlerts.tsx` — nav link updated to /filaments

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `const FilamentLibrary = () => <div>Filament Library — Phase 2 WIP</div>` | `frontend/src/App.tsx` | ~219 | Placeholder until Plan 05 creates the real FilamentLibrary component |

## Self-Check: PASSED

- `frontend/src/App.tsx` modified and committed
- `frontend/src/components/layout/AppLayout.tsx` modified and committed
- `backend/app/api/v1/modules.py` modified and committed
- `frontend/src/components/dashboard/LowStockAlerts.tsx` modified and committed
- Commits 0f65c93 and ddd2794 exist in git log
