# Batchivo — Filament Inventory Refinement

## What This Is

A focused refinement of Batchivo's filament tracking system. The current system has two duplicate routes (`/inventory` and `/filaments`) pointing at the same page, and a data model that conflates filament type definitions with individual physical spools. This project restructures the data model, consolidates the UI, and introduces frictionless workflows for bulk filament entry and label printing.

## Core Value

Every spool in the physical collection has a record in the system, a label, and a known status — with minimal effort to get it there.

## Requirements

### Validated

- ✓ Spool model exists with brand, color, material type, weight tracking, QR code, storage location — existing
- ✓ Label page exists at `/filaments/$spoolId/label` optimized for 54mm thermal printer — existing
- ✓ Material types table exists (PLA, PETG, etc.) as reference data — existing
- ✓ Multi-tenant RLS isolation in place — existing

### Active

- [ ] Consolidate `/inventory` and `/filaments` routes into a single `/filaments` route
- [ ] Introduce FilamentType model (brand, color, material type, diameter, temps, finish, pattern, notes)
- [ ] Migrate existing Spool records to FilamentType + Spool two-tier structure
- [ ] Add `has_sample` boolean to FilamentType (tracks whether a display benchy has been printed)
- [ ] Add `is_labeled` boolean to Spool (tracks whether physical label has been applied)
- [ ] Bulk add workflow: enter FilamentType once, set quantity, auto-generate N spool records
- [ ] Rapid mixed-batch add: pre-fills brand/type, step through each color variant quickly
- [ ] Label session: mobile-optimised queue of unlabeled spools, cycle through and mark labeled one at a time
- [ ] Filament list view aggregates by FilamentType showing spool count and status summary
- [ ] Individual spool detail view shows weight, label status, production history

### Out of Scope

- Direct Bluetooth printing to Nelko PM230 from browser — no public printer API; label session approach addresses the friction instead
- Full materials expansion (yarn, resin, consumables) — architecture must accommodate it but this project only implements filament
- Print calibration / slicer profile management — not part of this scope

## Context

**Existing system state:**
- `/inventory` and `/filaments` are route aliases for the same React page — one must be removed
- `Spool` model has `purchased_quantity`/`spools_remaining` fields that were an attempt to solve batch tracking — these will be superseded by the FilamentType split
- `SpoolLabelPage` exists but requires navigating to each spool individually on mobile, creating a jarring multi-step workflow
- Label printing uses a Nelko PM230 Bluetooth printer via the Android Nelko app — user screenshots the label page

**Data model direction:**
- FilamentType: the "what it is" — brand, color, material, diameter, temps, finish, pattern, `has_sample`
- Spool: individual physical spool — references FilamentType, has unique spool_id, weight, `is_labeled`, `is_active`
- This pattern extends naturally to MaterialVariant + MaterialUnit for future material types

**Label workflow target:**
- On laptop: add filaments → spools auto-queued as "needs label"
- On phone: open one URL (`/filaments/label-session`) → cycle through unlabeled spools → screenshot → print in Nelko app → tap "Labeled" → next

## Constraints

- **Tech Stack**: FastAPI + SQLAlchemy (async) + PostgreSQL — no framework changes
- **Migration Safety**: ~90 existing migrations in place; new migration must preserve existing spool data
- **Multi-Tenant**: All new models must include `tenant_id` with RLS enforcement
- **No Breaking Changes**: Existing production routes and API endpoints must remain functional during migration

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FilamentType + Spool two-tier model | Separates "what it is" from "individual unit" — avoids hundreds of near-duplicate records, enables aggregated views, extends to other material types | — Pending |
| `has_sample` on FilamentType | One benchy per filament type, not per spool — matches real-world workflow | — Pending |
| `is_labeled` on Spool | Each physical spool gets its own label — per-unit tracking | — Pending |
| Label session over direct Bluetooth printing | Nelko app has no web API; session page eliminates per-spool navigation friction on mobile | — Pending |
| Consolidate to `/filaments` (drop `/inventory`) | Single authoritative route; "inventory" is too generic for future (consumables, materials) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-19 after initialization*
