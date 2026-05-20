# Roadmap: Filament Inventory Refinement

## Overview

This project refactors Batchivo's filament tracking from a flat Spool model into a two-tier FilamentType + Spool structure, consolidates duplicate routes, and delivers end-to-end workflows for bulk adding and inspecting filament inventory. The migration is the riskiest work and goes first; each subsequent phase builds on a working foundation.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Model Migration** - Introduce FilamentType + Spool two-tier model and migrate existing spool data safely
- [ ] **Phase 2: Consolidated List View** - Collapse /inventory route and deliver aggregated FilamentType list UI
- [ ] **Phase 3: Add Workflows** - Bulk add and rapid mixed-batch add for creating FilamentType + Spool records
- [ ] **Phase 4: Detail Views** - FilamentType and individual Spool detail pages with status toggles

## Phase Details

### Phase 1: Data Model Migration

**Goal**: The database has FilamentType and refactored Spool models in place, with all existing spool data migrated intact
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):

  1. FilamentType records exist in the database, each with brand, color, material type, diameter, finish, pattern, temperatures, notes, and has_sample fields
  2. Every existing Spool record references a FilamentType and retains its original spool_id, weight, storage location, and QR code without data loss
  3. Spool records have an is_labeled boolean field (defaults false for migrated records)
  4. All new and migrated records are tenant-scoped; RLS enforcement passes for existing test suite
  5. FilamentType and Spool REST endpoints respond correctly (CRUD operations, auth, validation)

**Plans**: 7 plans
Plans:
**Wave 1**

- [ ] 01-01-PLAN.md — FilamentType model and schema hierarchy
- [ ] 01-02-PLAN.md — Spool model/schema updates, alembic env.py, merge migration

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-03-PLAN.md — Alembic data migration (create filament_types, backfill, restructure spools, RLS)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-04-PLAN.md — FilamentType CRUD API endpoints and module registration
- [ ] 01-05-PLAN.md — Updated Spool API endpoints (TenantDB fix, remove export/import)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-06-PLAN.md — Test fixtures and schema unit tests
- [ ] 01-07-PLAN.md — Integration tests for FilamentType API and updated Spool API tests

### Phase 2: Consolidated List View

**Goal**: Users navigate to a single /filaments route and see spools aggregated by FilamentType with status at a glance
**Depends on**: Phase 1
**Requirements**: NAV-01, NAV-02, LIST-01, LIST-02, LIST-03
**Success Criteria** (what must be TRUE):

  1. Navigating to /inventory redirects to or is removed in favour of /filaments; no 404s on internal links
  2. The filament list page groups spools by FilamentType showing type name and spool count (e.g., "JAYO Black PETG × 3")
  3. Each row shows how many spools are labeled and whether a sample has been printed
  4. User can filter or search the list by brand, color, material type, label status, or sample status

**Plans**: 8 plans
Plans:
**Wave 1** *(parallel — no file overlap)*

- [x] 02-01-PLAN.md — Route/nav surgery: /inventory redirect, sidebar nav deduplication, MODULE_NAVIGATION fix
- [x] 02-02-PLAN.md — Backend Pydantic schemas: FilamentTypeAggregatedResponse, FilamentTypeAggregatedListResponse, SpoolInSheetResponse

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-03-PLAN.md — Backend aggregation endpoints: GET /filament-types/aggregated + GET /{id}/spools
- [x] 02-04-PLAN.md — Frontend types + API client + TanStack Query hooks (useFilamentTypes, useFilamentTypeSpools, useToggleHasSample)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 02-05-PLAN.md — FilamentLibrary page + FilamentTypeCard (mobile) + FilamentTypeRow (desktop)
- [ ] 02-06-PLAN.md — FilamentTypeSpoolSheet + FilamentTypeFilterSheet + wire into FilamentLibrary

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 02-07-PLAN.md — Backend integration tests for aggregated endpoint + spools sub-resource
- [ ] 02-08-PLAN.md — Frontend tests: App.test.tsx (redirect) + FilamentTypeCard.test.tsx

### Phase 3: Add Workflows

**Goal**: Users can add filament to inventory quickly — either a batch of identical spools or a rapid run of color variants
**Depends on**: Phase 2
**Requirements**: ADD-01, ADD-02, ADD-03, ADD-04, ADD-05
**Success Criteria** (what must be TRUE):

  1. User can create a FilamentType and specify a quantity; that many Spool records are auto-generated with sequential spool IDs following the existing convention
  2. After a bulk add, newly created spools appear in the list with a "needs label" indicator
  3. User can enter brand and material type once, then add multiple color variants in rapid succession with those fields pre-filled; only color (and optionally finish/notes) is required per step

**Plans**: TBD
**UI hint**: yes

### Phase 4: Detail Views

**Goal**: Users can drill into any FilamentType or individual Spool to see full details and toggle status flags
**Depends on**: Phase 3
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05, VIEW-06
**Success Criteria** (what must be TRUE):

  1. FilamentType detail page shows all shared properties and lists all child Spool records with spool_id, current weight, is_labeled, and is_active
  2. User can toggle has_sample directly from the FilamentType detail page
  3. Individual Spool detail page shows weight, label status, storage location, production history, and QR code
  4. User can toggle is_labeled from the Spool detail page
  5. Spool detail page links back to its parent FilamentType

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Model Migration | 0/7 | Not started | - |
| 2. Consolidated List View | 5/9 | In Progress|  |
| 3. Add Workflows | 0/TBD | Not started | - |
| 4. Detail Views | 0/TBD | Not started | - |
