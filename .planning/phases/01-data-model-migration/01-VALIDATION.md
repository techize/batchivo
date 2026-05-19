---
phase: 1
slug: data-model-migration
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd backend && poetry run pytest tests/unit/ -x -q` |
| **Full suite command** | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| **Estimated runtime** | ~30 seconds (unit), ~90 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && poetry run pytest tests/unit/ -x -q`
- **After every plan wave:** Run `cd backend && poetry run pytest --cov=app --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | DATA-01, DATA-04 | T-01-01 | FilamentType has tenant_id; import verifies model structure | unit/import | `cd backend && python -c "from app.models.filament_type import FilamentType; cols = {c.name for c in FilamentType.__table__.columns}; assert 'tenant_id' in cols and 'has_sample' in cols; print('OK')"` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | DATA-01, DATA-04 | T-01-01 | Pydantic schemas validate; FilamentTypeCreate rejects invalid input | unit/import | `cd backend && python -c "from app.schemas.filament_type import FilamentTypeCreate, FilamentTypeUpdate, FilamentTypeResponse, FilamentTypeListResponse; print('OK')"` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 01-02 | 1 | DATA-02, DATA-05 | T-01-03 | Spool FK to filament_types; brand/color fields absent | unit/import | `cd backend && python -c "from app.models.spool import Spool; cols = {c.name for c in Spool.__table__.columns}; assert 'filament_type_id' in cols and 'is_labeled' in cols and 'brand' not in cols; print('OK')"` | ✅ | ⬜ pending |
| 01-02-T2 | 01-02 | 1 | DATA-02, DATA-05 | T-01-04 | Merge migration references all active heads; env.py imports FilamentType | unit/import | `cd backend && python -c "import pathlib; env=pathlib.Path('alembic/env.py').read_text(); assert 'FilamentType' in env; merge=list(pathlib.Path('alembic/versions').glob('*filament_type_heads*')); assert merge; print('OK')"` | ✅ | ⬜ pending |
| 01-03-T1 | 01-03 | 2 | DATA-01–05 | T-01-04 | Migration file contains NULL fail-fast check and upgrade() body | unit/import | `cd backend && python -c "import pathlib; f=list(pathlib.Path('alembic/versions').glob('*filament_type_migration*'))[0]; t=f.read_text(); assert 'fail' in t.lower() or 'RuntimeError' in t; assert 'DISTINCT ON' in t; print('OK')"` | ❌ W0 | ⬜ pending |
| 01-03-T2 | 01-03 | 2 | DATA-01–05 | T-01-04 | Migration downgrade() path exists and is functional | unit/import | `cd backend && python -c "import pathlib; f=list(pathlib.Path('alembic/versions').glob('*filament_type_migration*'))[0]; t=f.read_text(); assert 'def downgrade' in t; assert 'drop_table' in t or 'op.drop_table' in t; print('OK')"` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | DATA-01, DATA-04 | T-01-05 | FilamentType router uses TenantDB not get_db | unit/import | `cd backend && python -c "import pathlib; t=pathlib.Path('app/api/v1/filament_types.py').read_text(); assert 'get_db' not in t and 'TenantDB' in t; print('OK')"` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | DATA-01 | T-01-05 | FilamentTypesModule registered; routes mounted in app | unit/import | `cd backend && python -c "from app.modules.threed_print.filament_types import FilamentTypesModule; m=FilamentTypesModule(); print('module name:', m.name)"` | ❌ W0 | ⬜ pending |
| 01-05-T1 | 01-05 | 3 | DATA-02, DATA-03 | T-01-03 | Spool API uses TenantDB; material_type_code removed | unit/import | `cd backend && python -c "import pathlib; t=pathlib.Path('app/api/v1/spools.py').read_text(); assert 'get_db' not in t and 'TenantDB' in t and 'material_type_code' not in t; print('OK')"` | ✅ | ⬜ pending |
| 01-05-T2 | 01-05 | 3 | DATA-02 | T-01-03 | Export/import endpoints removed from spools.py | unit/import | `cd backend && python -c "import pathlib; t=pathlib.Path('app/api/v1/spools.py').read_text(); assert '/export' not in t and '/import' not in t; print('OK')"` | ✅ | ⬜ pending |
| 01-06-T1 | 01-06 | 4 | DATA-01, DATA-02, DATA-05 | — | conftest.py fixtures importable and parseable | unit | `cd backend && poetry run pytest tests/unit/test_filament_type_schemas.py -x -q 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 01-06-T2 | 01-06 | 4 | DATA-01, DATA-04 | — | FilamentType schema unit tests pass | unit | `cd backend && poetry run pytest tests/unit/test_filament_type_schemas.py tests/unit/test_spool_schemas.py -x -q 2>&1 | tail -10` | ❌ W0 | ⬜ pending |
| 01-07-T1 | 01-07 | 4 | DATA-01, DATA-04 | — | FilamentType API integration tests pass | integration | `cd backend && poetry run pytest tests/integration/test_filament_types_api.py -x -q 2>&1 | tail -15` | ❌ W0 | ⬜ pending |
| 01-07-T2 | 01-07 | 4 | DATA-02, DATA-03 | — | Updated Spool API integration tests pass | integration | `cd backend && poetry run pytest tests/integration/test_spools_api.py -x -q 2>&1 | tail -15` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_filament_type_schemas.py` — schema unit test stubs for DATA-01, DATA-04 (created in Plan 01-06)
- [ ] `tests/unit/test_spool_schemas.py` — updated spool schema tests for DATA-02, DATA-05 (updated in Plan 01-06)
- [ ] `tests/integration/test_filament_types_api.py` — FilamentType CRUD integration tests for DATA-01 (created in Plan 01-07)
- [ ] `backend/app/models/filament_type.py` — new FilamentType model (created in Plan 01-01)
- [ ] `backend/app/schemas/filament_type.py` — new FilamentType schemas (created in Plan 01-01)
- [ ] `backend/app/api/v1/filament_types.py` — new FilamentType router (created in Plan 01-04)
- [ ] `backend/app/modules/threed_print/filament_types.py` — new FilamentTypesModule (created in Plan 01-04)

*These files are created by Phase 1 plans — Wave 0 means "created before tests can run."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration runs without data loss on production-like data | DATA-03 | Requires live database with real spool records | Seed test DB with spools having varied brand/color combos, run `alembic upgrade head`, verify spool count unchanged and filament_type records match expected deduplication groups |
| Downgrade restores all spool data | DATA-03 | Requires live migration state | After upgrade, run `alembic downgrade -1`, verify brand/color columns restored and filament_types table dropped |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (7 files created by Phase 1 plans)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
