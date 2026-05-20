# Requirements: Filament Inventory Refinement

**Defined:** 2026-05-19
**Core Value:** Every spool in the physical collection has a record in the system, a label, and a known status — with minimal effort to get it there.

## v1 Requirements

### Data Model

- [ ] **DATA-01**: System has a FilamentType model storing brand, color, material type, diameter, finish, pattern, temperatures, and notes as a shared definition record
- [ ] **DATA-02**: Spool model references FilamentType instead of duplicating all filament properties; retains unique spool_id, weight, storage location, QR code, is_active
- [ ] **DATA-03**: Existing Spool records are migrated to the new two-tier structure without data loss (spool data preserved, FilamentType records inferred/created from existing spool data)
- [ ] **DATA-04**: FilamentType has `has_sample` boolean field tracking whether a display benchy has been printed for this filament type
- [ ] **DATA-05**: Spool has `is_labeled` boolean field tracking whether a physical label has been applied to the individual spool

### Routing & Navigation

- [x] **NAV-01**: `/inventory` route is removed; all filament spool content lives exclusively at `/filaments`
- [x] **NAV-02**: Any internal links or navigation pointing to `/inventory` are updated to `/filaments`

### Filament List View

- [x] **LIST-01**: Filament list page aggregates spools by FilamentType, showing type name and spool count (e.g., "JAYO Black PETG × 3")
- [x] **LIST-02**: Each FilamentType row shows a status summary: how many spools are labeled, and whether a sample has been printed
- [x] **LIST-03**: User can filter/search by brand, color, material type, or label/sample status

### Add Workflow — Bulk

- [ ] **ADD-01**: User can add a new FilamentType and specify a quantity; system auto-generates that many Spool records with sequential spool IDs
- [ ] **ADD-02**: Auto-generated spool IDs follow the existing spool_id convention (e.g., FIL-001, FIL-002)
- [ ] **ADD-03**: After bulk add, newly created spools appear in the list as "needs label" with clear visual indicator

### Add Workflow — Rapid Mixed Batch

- [ ] **ADD-04**: User can enter a brand and material type once, then step through adding multiple color variants rapidly with those fields pre-filled
- [ ] **ADD-05**: Each step in the rapid batch flow requires only color (and optionally finish/notes) to create a new FilamentType + initial spool

### FilamentType Detail View

- [ ] **VIEW-01**: FilamentType detail page shows all shared properties and lists all child Spool records
- [ ] **VIEW-02**: Each Spool in the list shows: spool_id, current weight, is_labeled status, is_active status
- [ ] **VIEW-03**: User can toggle `has_sample` from the FilamentType detail page

### Individual Spool Detail View

- [ ] **VIEW-04**: Individual Spool detail page shows: weight, label status, storage location, production history, QR code
- [ ] **VIEW-05**: User can toggle `is_labeled` from the Spool detail page
- [ ] **VIEW-06**: Spool detail links back to its parent FilamentType

## v2 Requirements

### Label Session (Mobile Workflow)

- **LABEL-01**: Label session page (`/filaments/label-session`) shows a queue of all unlabeled spools optimised for mobile use
- **LABEL-02**: User can cycle through spools one at a time, view the label (screenshot for Nelko app), then mark labeled with one tap
- **LABEL-03**: After adding a batch on laptop, unlabeled spools are automatically queued for the label session

### API & Integration

- **API-01**: FilamentType and Spool endpoints exposed via REST API for potential future integrations (SpoolMan, AMS slot mapping)
- **API-02**: Bulk spool creation endpoint accepts FilamentType definition + quantity in a single request

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct Bluetooth printing to Nelko PM230 | No public web API for Nelko printers; label session approach addresses friction without requiring direct integration |
| Full materials expansion (yarn, resin, consumables) | Architecture must accommodate it but implementation is out of scope for this project |
| Print calibration / slicer profile management | Different problem domain — not filament inventory |
| SpoolMan database sync | Existing feature; not being touched in this refactor |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| NAV-01 | Phase 2 | Complete |
| NAV-02 | Phase 2 | Complete |
| LIST-01 | Phase 2 | Complete |
| LIST-02 | Phase 2 | Complete |
| LIST-03 | Phase 2 | Complete |
| ADD-01 | Phase 3 | Pending |
| ADD-02 | Phase 3 | Pending |
| ADD-03 | Phase 3 | Pending |
| ADD-04 | Phase 3 | Pending |
| ADD-05 | Phase 3 | Pending |
| VIEW-01 | Phase 4 | Pending |
| VIEW-02 | Phase 4 | Pending |
| VIEW-03 | Phase 4 | Pending |
| VIEW-04 | Phase 4 | Pending |
| VIEW-05 | Phase 4 | Pending |
| VIEW-06 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-19*
*Last updated: 2026-05-19 after initial definition*
