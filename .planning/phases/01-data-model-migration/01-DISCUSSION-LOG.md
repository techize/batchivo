# Phase 1: Data Model Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 1-Data Model Migration
**Areas discussed:** Field split, Deduplication key, Deprecated field removal

---

## Field Split

### purchase_price, supplier, purchase_date

| Option | Description | Selected |
|--------|-------------|----------|
| Per-FilamentType | All spools of same type treated as one purchase | |
| Per-Spool | Individual spools may come from different purchases | ✓ |
| Both (defaults + override) | FilamentType stores typical info; Spool can override | |

**User's choice:** Per-Spool
**Notes:** Purchase info is per individual spool acquisition, not per type definition.

---

### color_hex

| Option | Description | Selected |
|--------|-------------|----------|
| FilamentType | All spools of JAYO Black PETG share the same hex | ✓ |
| Spool | Individual spools might vary by batch | |

**User's choice:** FilamentType

---

### translucent, glow, spool_type

| Option | Description | Selected |
|--------|-------------|----------|
| FilamentType | Intrinsic properties of filament formulation | ✓ |
| Spool | Rare edge case where batch varies | |

**User's choice:** FilamentType

---

### density, extruder_temp, bed_temp

| Option | Description | Selected |
|--------|-------------|----------|
| FilamentType | Manufacturer specs for the formulation | ✓ |
| Spool | Calibrated per individual spool | |

**User's choice:** FilamentType

---

## Deduplication Key

### Uniqueness key for inferring FilamentType from existing spools

| Option | Description | Selected |
|--------|-------------|----------|
| brand + color + material_type_id + diameter | Full identity including diameter | |
| brand + color + material_type_id | Core identity — diameter differences ignored | ✓ |
| All FilamentType fields | Strictest match — any difference creates separate type | |

**User's choice:** brand + color + material_type_id (no diameter)

---

### Which spool's values populate shared FilamentType fields when deduplicating

| Option | Description | Selected |
|--------|-------------|----------|
| First spool (by created_at) | Oldest record wins | ✓ |
| Most-used values | Most common value across matching spools | |
| NULL / empty | User fills in after migration | |

**User's choice:** First spool by created_at

---

### Handling spools with NULL brand or NULL color

| Option | Description | Selected |
|--------|-------------|----------|
| Create 'Unknown' FilamentType per material_type | Group incomplete spools under placeholder | |
| Create one FilamentType per incomplete spool | No merging, more records | |
| Fail migration if NULL brand/color found | Surface data issues explicitly | ✓ |

**User's choice:** Fail migration — surface NULL data issues before proceeding.

---

## Deprecated Field Removal

### When to remove purchased_quantity and spools_remaining

| Option | Description | Selected |
|--------|-------------|----------|
| Remove in Phase 1 migration (clean break) | Drop in same migration as FilamentType creation | ✓ |
| Keep nullable in Phase 1, remove in Phase 2 | Staged removal for safety | |
| Keep indefinitely | Leave as historical data | |

**User's choice:** Remove in Phase 1 — clean break.

---

### Migration downgrade() path

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — full rollback path | downgrade() reverses all changes | ✓ |
| No — one-way migration | Rollback via DB restore only | |

**User's choice:** Full downgrade() path required.

---

## Claude's Discretion

None — user made explicit choices on all questions.

## Deferred Ideas

None — discussion stayed within Phase 1 scope.
