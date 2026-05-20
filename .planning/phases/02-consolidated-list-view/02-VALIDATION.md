---
phase: 2
slug: consolidated-list-view
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-20
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Vitest (frontend) |
| **Config file** | `backend/pyproject.toml` / `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && poetry run pytest tests/api/test_filament_types.py -x -q` |
| **Full suite command** | `cd backend && poetry run pytest && cd ../frontend && npm test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && poetry run pytest tests/api/test_filament_types.py -x -q`
- **After every plan wave:** Run `cd backend && poetry run pytest && cd ../frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | NAV-01, NAV-02 | — | Redirect enforces tenant auth before redirect | unit | `cd backend && poetry run pytest tests/api/test_filament_types.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | NAV-01, NAV-02 | — | /inventory → /filaments redirect, no 404s | integration | `cd frontend && npm test -- --run App.test` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 0 | LIST-01, LIST-02 | — | Aggregation respects tenant_id scope | unit | `cd backend && poetry run pytest tests/api/test_filament_types.py::test_aggregated -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | LIST-01, LIST-02 | — | FilamentType groups show correct spool counts | integration | `cd backend && poetry run pytest tests/api/test_filament_types.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | LIST-03 | — | Filter params scoped to tenant | unit | `cd backend && poetry run pytest tests/api/test_filament_types.py::test_filter -x -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | LIST-03 | — | Filter/search UI updates query correctly | e2e | `cd frontend && npm test -- --run FilamentList.test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/test_filament_types.py` — aggregation + filter + sub-resource stubs for NAV-01, NAV-02, LIST-01, LIST-02, LIST-03
- [ ] `frontend/src/App.test.tsx` — redirect verification for NAV-01, NAV-02
- [ ] `frontend/src/components/FilamentList.test.tsx` — filter/search UI stubs for LIST-03

*Existing infrastructure (conftest.py fixtures: test_tenant, test_spool, test_filament_type) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual grouping layout matches UI-SPEC | LIST-01 | CSS/visual testing not automated | Load /filaments in browser, verify FilamentType rows with badge counts render per UI-SPEC §3 |
| Filter panel UX (open/close Sheet) | LIST-03 | Interaction flow | Open filter panel, apply brand filter, verify list updates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
