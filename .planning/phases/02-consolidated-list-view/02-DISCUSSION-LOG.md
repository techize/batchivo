# Phase 2: Consolidated List View - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 02-consolidated-list-view
**Areas discussed:** Spool Access During Phase 2, API Aggregation Approach, Filter Panel Scope and Layout, /inventory Removal Strategy, Row Design

---

## Spool Access During Phase 2

| Option | Description | Selected |
|--------|-------------|----------|
| Expand in-place (accordion) | Click row to reveal child spools inline with actions | |
| Open a slide-over / sheet | Click opens Sheet component listing child spools | ✓ |
| No drill-down — defer to Phase 4 | Read-only list until Phase 4 detail pages | |

**User's choice:** Open a slide-over / sheet

| Option | Description | Selected |
|--------|-------------|----------|
| Full set — Update Weight, Edit, QR label, Delete | Everything the old SpoolList had | |
| Core only — Update Weight + QR label link | Most-used actions on mobile | |
| Read-only in sheet — just show spool details | No mutating actions until Phase 4 | ✓ |

**User's choice:** Read-only sheet — spool details only, no actions

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle has_sample inline on the row | Quick checkbox on the FilamentType row | ✓ |
| No inline actions — everything inside the sheet | Keep list visually clean | |
| You decide | Claude discretion | |

**User's choice:** Toggle has_sample inline on the FilamentType row

---

## API Aggregation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| New backend endpoint — FilamentType list with computed counts | Dedicated endpoint, DB-level aggregation | ✓ |
| Frontend groups spool data client-side | Fetch spools, group by filament_type_id in component | |

**User's choice:** New backend endpoint with pre-computed counts

| Option | Description | Selected |
|--------|-------------|----------|
| Core only — id, brand, color, material_type, spool_count, labeled_count, has_sample | Lean list payload | ✓ |
| Full FilamentType fields + counts | All properties including temps, diameter, etc. | |

**User's choice:** Core fields only — sheet fetches full detail separately

| Option | Description | Selected |
|--------|-------------|----------|
| Separate fetch — GET /api/v1/filament-types/{id}/spools | New sub-resource endpoint | ✓ |
| Reuse existing GET /api/v1/spools?filament_type_id={id} | Filter existing spools endpoint | |

**User's choice:** Separate sub-resource endpoint

---

## Filter Panel Scope and Layout

| Option | Description | Selected |
|--------|-------------|----------|
| All 5 — brand, color, material type, label status, sample status | Full LIST-03 coverage | ✓ |
| Core 3 — material type, label status, sample status | Brand/color via search box only | |

**User's choice:** All 5 filter dimensions

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsible filter card (same as current SpoolList) | Consistent with existing pattern | |
| Always-visible compact filter bar above the list | Compact, always shown | |
| Filter icon + popover/sheet (mobile-first) | Filter button opens a sheet | ✓ |

**User's choice:** Filter icon + sheet (mobile-first)

| Option | Description | Selected |
|--------|-------------|----------|
| Search box + Filter button side by side | Two-element header | ✓ |
| Search box only; filter button appears after typing | Minimal default state | |

**User's choice:** Search box + Filter button always visible

| Option | Description | Selected |
|--------|-------------|----------|
| Three-state toggle: All / Has unlabeled / All labeled | Status progression | |
| Separate toggles: "Needs labels" and "No sample" | Two independent chips | |
| You decide | Claude discretion | ✓ |

**Notes:** User deferred this to Claude. Decision: separate independent toggles matching the existing "Low Stock Only" pattern.

---

## /inventory Removal Strategy

**Context:** User raised the question of whether `/materials` would be a better route name for future extensibility. After discussing:
- Existing `/yarn` route shows material types get their own feature-specific routes, not a `/materials` umbrella
- Existing sub-routes (`/filaments/scan`, `/filaments/$spoolId/label`) would break under a rename
- A cross-material hub would be its own architectural phase, not a rename

**Decision: Keep `/filaments` as canonical route.**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep /filaments, client-side redirect from /inventory | TanStack Router redirect | ✓ |
| Keep /filaments, hard remove /inventory | Clean break, risk of 404s | |

**User's choice:** Client-side redirect (production-critical — external bookmarks may exist)

| Option | Description | Selected |
|--------|-------------|----------|
| Internal only — just sidebar nav and in-app links | Audit scope is App.tsx + sidebar | |
| Possibly external — treat as production-critical | External bookmarks/docs may link to /inventory | ✓ |

**User's choice:** Treat as production-critical

| Option | Description | Selected |
|--------|-------------|----------|
| Single entry — "Filaments" linking to /filaments | Remove "Inventory" duplicate | ✓ |
| Rename to "Filaments" and keep position | Same thing, with explicit position note | |

**User's choice:** Single "Filaments" nav entry

---

## Row Design

| Option | Description | Selected |
|--------|-------------|----------|
| Color swatch dot + color name | Filled circle using color_hex | |
| Color name only | Text only | |
| You decide | Claude discretion | ✓ |

**Notes:** Claude to use color swatch when color_hex is available, match existing SpoolCard pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| Badges — "3 spools", "2/3 labeled", "Sample ✓/✗" | Three compact badges | ✓ |
| Inline text with icons | Icon + count inline | |
| Progress-style — progress bar for labeled/total | Visual bar, more space | |

**User's choice:** Badge layout

| Option | Description | Selected |
|--------|-------------|----------|
| Card layout — consistent with existing SpoolCard | Mobile follows SpoolCard pattern | ✓ |
| Compact list row — simpler than SpoolCard | Thinner row, more items visible | |

**User's choice:** Card layout on mobile (consistent with SpoolCard)

---

## Claude's Discretion

- Color display: swatch dot when `color_hex` available, text-only fallback — match SpoolCard.tsx pattern
- Label/sample status filter toggles: separate independent toggles matching existing "Low Stock Only" button pattern
- `has_sample` toggle styling: visually distinct to avoid accidental taps during scroll (small checkbox or icon button, not full-row click target)

## Deferred Ideas

- `/materials` as a generic route hub for all material types — separate architectural phase
- Per-spool Edit / Delete / Update Weight in the sheet — deferred to Phase 4 detail pages
- Color-based grouping within rows (e.g., color grid showing all shades of a brand) — out of scope Phase 2
