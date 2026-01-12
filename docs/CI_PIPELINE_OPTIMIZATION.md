# CI/CD Pipeline Optimization Analysis

**Date**: 2025-01-09
**Current Pipeline Time**: ~57 minutes
**Target Pipeline Time**: <10 minutes

---

## Executive Summary

The batchivo.com CI pipeline takes ~57 minutes, with **backend tests consuming 91% of that time** (52 minutes for 1,832 tests). This document identifies the bottlenecks and proposes concrete optimizations to achieve sub-10-minute deployments without compromising test coverage.

---

## Current State Analysis

### Pipeline Timing Breakdown

| Stage | Duration | % of Total | Parallelizable |
|-------|----------|------------|----------------|
| clone | 12s | 0.4% | N/A |
| scan-deps-backend | 47s | 1.4% | Yes (already parallel) |
| scan-deps-frontend | 36s | 1.1% | Yes (already parallel) |
| **backend tests** | **52 min** | **91%** | **Critical bottleneck** |
| frontend tests | 37s | 1.1% | Yes (already parallel) |
| build-backend | ~3 min | 5% | Yes |
| build-frontend | ~3 min | 5% | Yes |
| scan-backend | ~1 min | 2% | After build |
| scan-frontend | ~1 min | 2% | After build |
| deploy-staging | 30s | 1% | Sequential |
| health-check | 2 min | 3% | Sequential |
| deploy-production | 30s | 1% | Sequential |

### Backend Test Analysis

```
Total tests: 1,832
Test files: 91 (38 unit + 29 integration + 24 API)
Average time per test: 1.7 seconds
```

**Root Causes of Slow Tests:**
1. **Function-scoped database fixtures** - Each test creates/drops all tables
2. **No parallel execution** - Tests run sequentially
3. **Full PostgreSQL schema recreation** per test function
4. **No dependency caching** - Poetry install every build

### Current Pipeline Architecture

```
scan-deps-backend ─┐
                   ├─> backend ──────────────────────────────────> build-backend -> scan-backend ─┐
scan-deps-frontend ─┘                                                                             │
                   └─> frontend -> build-frontend -> scan-frontend ────────────────────────────────┼─> deploy-staging -> health-check -> deploy-production
```

---

## Optimization Strategies

### 1. Parallel Test Execution (Impact: HIGH - saves ~40 min)

**Add pytest-xdist** for parallel test execution:

```toml
# pyproject.toml - add to dev dependencies
pytest-xdist = "^3.5.0"
```

```yaml
# build.yml - backend step
commands:
  - poetry run pytest tests/ -n auto --dist worksteal -q
```

**Expected improvement**: With 8 workers, ~52 min → ~7-10 min

### 2. Test Fixture Optimization (Impact: MEDIUM - saves ~20%)

**Option A: Session-scoped engine with transaction rollback**

```python
# conftest.py - Change fixture scope
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create engine once per session, not per test."""
    # ... existing code but session-scoped

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Each test gets a transaction that rolls back."""
    async with db_engine.begin() as conn:
        # Start savepoint
        yield conn
        await conn.rollback()  # Rollback instead of table drop
```

**Option B: Use pytest-postgresql plugin** for managed test databases

### 3. Split Test Pipeline (Impact: MEDIUM - enables parallelization)

Split backend tests into parallel steps:

```yaml
steps:
  backend-unit:
    image: *python_image
    commands:
      - poetry run pytest tests/unit/ -n auto -q

  backend-integration:
    image: *python_image
    commands:
      - poetry run pytest tests/integration/ -n auto -q

  backend-api:
    image: *python_image
    commands:
      - poetry run pytest tests/api/ -n auto -q
```

With 3 parallel test steps + internal parallelization, expected time: ~3-5 min

### 4. Dependency Caching (Impact: LOW - saves 3-5 min)

**Add S3 cache plugin**:

```yaml
steps:
  restore-cache:
    image: woodpeckerci/plugin-s3-cache
    settings:
      restore: true
      endpoint: s3.techize.co.uk  # MinIO endpoint
      bucket: ci-cache
      mount:
        - backend/.venv
        - frontend/node_modules
      access_key:
        from_secret: s3_access_key
      secret_key:
        from_secret: s3_secret_key

  # ... test steps ...

  rebuild-cache:
    image: woodpeckerci/plugin-s3-cache
    settings:
      rebuild: true
      # ... same settings
    when:
      - event: push
        branch: main
```

### 5. Early Docker Builds (Impact: LOW - saves 2-3 min)

Start Docker builds earlier, only security scans need test success:

```yaml
# New architecture
steps:
  # Tests and builds in parallel
  backend-tests:
    # ...

  frontend-tests:
    # ...

  build-backend:
    depends_on: [scan-deps-backend]  # Don't wait for tests!

  build-frontend:
    depends_on: [scan-deps-frontend]  # Don't wait for tests!

  # Security scans gate deployment
  scan-backend:
    depends_on: [build-backend, backend-tests]  # Both must pass

  deploy:
    depends_on: [scan-backend, scan-frontend, frontend-tests]
```

### 6. Pre-built Test Base Image (Impact: MEDIUM - saves 2-3 min per build)

Create a base image with dependencies pre-installed:

```dockerfile
# Dockerfile.test
FROM python:3.12-slim
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction
```

Build and push on dependency changes only.

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1 day, saves ~35-40 min)

1. **Add pytest-xdist** - Single line in pyproject.toml + pipeline change
2. **Run with -n auto** - Immediate ~4-6x speedup

**Expected pipeline time after Phase 1: ~15-20 min**

### Phase 2: Pipeline Restructuring (2-3 days, saves ~5-8 min)

1. Split tests into parallel steps (unit/integration/api)
2. Start Docker builds earlier
3. Add dependency caching

**Expected pipeline time after Phase 2: ~8-12 min**

### Phase 3: Test Infrastructure (3-5 days, saves ~2-5 min)

1. Optimize fixtures to use session scope + transaction rollback
2. Create pre-built test base image
3. Consider test database pooling

**Expected pipeline time after Phase 3: ~5-8 min**

---

## Optimized Pipeline Architecture (Target State)

```yaml
when:
  - event: push
    branch: main

steps:
  # ===== Parallel Test Preparation =====
  restore-cache:
    image: woodpeckerci/plugin-s3-cache
    settings:
      restore: true
      # ...

  # ===== Parallel Tests (with internal parallelization) =====
  backend-unit:
    image: *python_image_cached
    depends_on: [restore-cache]
    commands:
      - poetry run pytest tests/unit/ -n 4 --dist worksteal -q

  backend-integration:
    image: *python_image_cached
    depends_on: [restore-cache]
    commands:
      - poetry run pytest tests/integration/ -n 4 --dist worksteal -q

  backend-api:
    image: *python_image_cached
    depends_on: [restore-cache]
    commands:
      - poetry run pytest tests/api/ -n 4 --dist worksteal -q

  frontend:
    image: *node_image
    depends_on: [restore-cache]
    commands:
      - npm run lint && npm run typecheck && npm test -- --run

  # ===== Parallel Builds (start immediately) =====
  build-backend:
    image: plugins/kaniko
    depends_on: [scan-deps-backend]  # Don't wait for tests
    # ...

  build-frontend:
    image: plugins/kaniko
    depends_on: [scan-deps-frontend]  # Don't wait for tests
    # ...

  # ===== Security Scans (gate on tests + builds) =====
  scan-backend:
    depends_on: [build-backend, backend-unit, backend-integration, backend-api]
    # ...

  scan-frontend:
    depends_on: [build-frontend, frontend]
    # ...

  # ===== Deployment =====
  deploy-staging:
    depends_on: [scan-backend, scan-frontend]
    # ...
```

---

## Quick Implementation: Phase 1

### Step 1: Add pytest-xdist

```bash
cd backend
poetry add --group dev pytest-xdist
```

### Step 2: Update build.yml

```yaml
backend:
  image: *python_image
  environment:
    DATABASE_URL: postgresql+psycopg://test:test@postgres:5432/test_batchivo
    SECRET_KEY: test-secret-key-for-ci
  commands:
    - cd backend
    - pip install --quiet poetry
    - poetry install --no-interaction --quiet
    - echo "=== Running linters ==="
    - poetry run ruff check .
    - poetry run ruff format --check .
    - echo "=== Running tests (parallel) ==="
    - poetry run pytest tests/ -n auto --dist worksteal -q
```

### Expected Results After Phase 1

| Metric | Before | After |
|--------|--------|-------|
| Backend test time | 52 min | ~10-12 min |
| Total pipeline time | 57 min | ~15-18 min |
| Deployment frequency | Limited | Viable |

---

## Risks and Considerations

1. **Test Isolation**: pytest-xdist requires tests to be independent. Current function-scoped fixtures should ensure this, but verify.

2. **Database Contention**: With parallel tests hitting the same DB, may need test database per worker or careful transaction isolation.

3. **CI Resources**: More parallel workers = more CPU/memory. Monitor Woodpecker agent resources.

4. **Flaky Tests**: Parallelization can expose race conditions. Monitor for flaky tests post-implementation.

---

## Conclusion

The biggest win is **adding pytest-xdist** - a single dependency and config change that can reduce pipeline time from 57 minutes to ~15-18 minutes. This should be implemented immediately.

Further optimizations can bring the pipeline to under 10 minutes, but the ROI decreases after Phase 1. Prioritize based on development velocity needs.
