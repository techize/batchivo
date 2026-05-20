---
phase: 03
slug: add-workflows
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && poetry run pytest tests/integration/test_filament_types_api.py -x` |
| **Full suite command** | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| **Frontend unit tests** | `cd frontend && npm run test` (Vitest) |
| **Estimated runtime** | ~30 seconds (integration), ~2 min (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && poetry run pytest tests/integration/test_filament_types_api.py -x`
- **After every plan wave:** Run `cd backend && poetry run pytest --cov=app --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | ADD-01 | — | N/A | unit | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | ADD-04 | — | N/A | unit | `pytest tests/integration/test_filament_types_api.py::TestBatchCreate -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | ADD-01, ADD-02 | T-cross-tenant | `tenant_id` injected from JWT, never from request body | integration | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | ADD-02 | T-spool-id-injection | IDs are server-generated; no `spool_id` in request body | integration | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate::test_spool_id_format -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 1 | ADD-03 | — | N/A | integration | `pytest tests/integration/test_filament_types_api.py::TestBulkCreate -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 1 | ADD-04, ADD-05 | T-cross-tenant | `tenant_id` injected from JWT | integration | `pytest tests/integration/test_filament_types_api.py::TestBatchCreate -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 1 | ADD-05 | — | N/A | integration | same | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | ADD-01 | — | N/A | unit | `cd frontend && npm run test -- AddFilamentDialog` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 2 | ADD-04 | — | N/A | unit | same | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/test_filament_types_api.py` — add `TestBulkCreate` and `TestBatchCreate` test classes (file exists, classes don't)
- [ ] `frontend/src/components/filaments/AddFilamentDialog.test.tsx` — create test file covering Dialog state machine, form submission, query invalidation
- [ ] Fixtures: `test_material_type`, `test_filament_type`, `test_spool` already exist in `backend/tests/conftest.py` — no new fixtures needed

*Wave 0 must be complete before Wave 1 execution tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mode selector visual hierarchy (icon → title → description) | ADD-01, ADD-04 | CSS/visual verification | Open dialog, confirm card layout matches 03-UI-SPEC.md §Layout Contract |
| Rapid batch — last-used brand/material pre-fills on next row | ADD-05 | State machine interaction | Add first row with brand+material+color, click "Add Filament" → new row; confirm brand+material fields pre-populated |
| Back button preserves form state across mode switches | D-22, D-23 | Multi-step navigation | Fill bulk form fields, click Back to mode selector, click Rapid Batch — confirm state is NOT preserved (isolated modes) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
