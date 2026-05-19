# Testing Patterns

**Analysis Date:** 2026-05-19

## Backend Test Framework

**Runner:**
- `pytest` 9.x with `pytest-asyncio` 1.3.x
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async tests run automatically without explicit marks
- `asyncio_default_fixture_loop_scope = "function"` — fresh event loop per test
- Timeout: 300 seconds per test (`pytest-timeout`)
- Parallel execution: `pytest-xdist` with worker-isolated databases

**Key test dependencies:**
- `httpx` + `ASGITransport` — in-process ASGI test client
- `fakeredis` — Redis mocking for most tests
- `moto[s3]` — AWS S3 mocking
- `respx` — HTTP client mocking for external API calls (used in `test_moonraker_adapter.py`)

**Run Commands:**
```bash
cd backend && poetry run pytest                              # Run all tests
cd backend && poetry run pytest tests/unit/                 # Unit tests only
cd backend && poetry run pytest tests/integration/          # Integration tests only
cd backend && poetry run pytest tests/api/                  # API endpoint tests only
cd backend && poetry run pytest --cov=app --cov-report=term-missing  # With coverage
cd backend && poetry run pytest -n auto                     # Parallel (xdist)
```

## Frontend Test Framework

**Runner:**
- `vitest` with jsdom environment
- Config: `frontend/vitest.config.ts`
- Globals enabled — no need to import `describe`, `it`, `expect`
- Setup file: `frontend/src/test/setup.ts`
- Coverage: `v8` provider, thresholds at 30% (statements, branches, functions, lines)

**Key test dependencies:**
- `@testing-library/react` + `@testing-library/jest-dom` — component testing
- `@playwright/test` — E2E browser tests
- `vitest` mocking via `vi.mock()`, `vi.fn()`, `vi.mocked()`

**Run Commands:**
```bash
cd frontend && npm test                     # Watch mode
cd frontend && npm run test:run             # Single run
cd frontend && npm run test:coverage        # With coverage report
cd frontend && npm run test:ci              # CI mode (junit output)
cd frontend && npm run test:e2e             # Playwright E2E
cd frontend && npm run test:e2e:headed      # E2E with browser visible
```

## Backend Test File Organization

**Location:**
- Tests in `backend/tests/` — separate from application code
- Three subdirectories: `unit/`, `integration/`, `api/`
- Shared fixtures in `backend/tests/conftest.py`
- Test utilities in `backend/tests/utils/`

**Naming:**
- All files: `test_<subject>.py`
- Unit tests: `test_<service_name>.py` or `test_<schema_name>.py`
- Integration tests: `test_<resource>_api.py`
- API tests: `test_<endpoint_name>.py`

**Structure:**
```
backend/tests/
├── conftest.py                    # All shared fixtures
├── api/                           # API endpoint tests (with auth overrides)
│   ├── test_spools.py
│   ├── test_products.py
│   └── ...
├── integration/                   # Integration tests (real DB, no auth bypass)
│   ├── test_auth_api.py
│   ├── test_production_runs_api.py
│   └── ...
├── unit/                          # Unit tests (service/schema logic)
│   ├── test_production_run_service.py
│   ├── test_security.py
│   └── ...
└── utils/
    └── mock_redis.py              # Custom Redis mock for Lua script support
```

## Backend Test Structure

**Suite Organization:**
```python
"""Tests for spool API endpoints."""

class TestCreateSpool:
    """Tests for spool creation endpoint."""

    async def test_create_spool(self, client: AsyncClient, test_material_type: MaterialType):
        """Test creating a new spool."""
        response = await client.post("/api/v1/spools", json={...})
        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] == "NEW-SPOOL-001"

    async def test_create_spool_invalid_material(self, client: AsyncClient):
        """Test that invalid material_type_id returns 400."""
        response = await client.post("/api/v1/spools", json={...})
        assert response.status_code == 400
```

**Patterns:**
- Group tests by resource operation using classes (e.g., `TestCreateSpool`, `TestUpdateSpool`)
- Each test method has a docstring describing what it tests
- Async test methods do NOT need `@pytest.mark.asyncio` (set globally via `asyncio_mode = "auto"`)
- Some older tests use `@pytest.mark.asyncio` or `@pytest.mark.anyio` (inconsistency exists)
- Section dividers `# ============================================` separate fixtures from test classes

## Backend Mocking

**Dependency Injection Overrides (primary pattern for API tests):**
```python
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_current_tenant] = override_get_current_tenant
```
Overrides are set in `conftest.py` `client` fixture and cleared after each test.

**`unittest.mock` for external services:**
```python
from unittest.mock import AsyncMock, MagicMock, patch

# Patching settings
with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
    ...

# Mocking async methods
db.execute = AsyncMock(return_value=MagicMock())
```

**`moto` for AWS S3:**
```python
@pytest.fixture
def s3_mock():
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=TEST_S3_BUCKET)
        yield conn
```

**`respx` for outbound HTTP:**
```python
with respx.mock:
    respx.get(f"{BASE_URL}/printer/objects/query").mock(
        return_value=httpx.Response(200, json={...})
    )
```

**`MockRedis` custom class** (`backend/tests/utils/mock_redis.py`):
Used when `fakeredis` is insufficient (Lua script / `register_script` support).

**What to Mock:**
- External HTTP calls (Square, Moonraker, Etsy) — always mock
- AWS S3 operations — use `moto`
- Redis — use `fakeredis` or `MockRedis` depending on Lua script needs
- Auth dependencies — override via `app.dependency_overrides`
- Settings/config — use `MagicMock()` or `patch`

**What NOT to Mock:**
- Database operations — use real async session against test DB (SQLite or PostgreSQL)
- Pydantic validation — test directly against schemas
- Internal service logic — test against real service instances

## Backend Fixtures

**Core fixtures** (defined in `backend/tests/conftest.py`):

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_engine` | function | Creates and tears down test database schema |
| `db_session` | function | `AsyncSession` per test, rolls back after |
| `client` | function | `AsyncClient` with auth + DB overrides |
| `unauthenticated_client` | function | `AsyncClient` with DB override only (for auth tests) |
| `customer_client` | function | `AsyncClient` authenticated as customer |
| `test_tenant` | function | `Tenant` with unique slug |
| `test_user` | function | `User` with ADMIN role in test tenant |
| `test_spool` | function | `Spool` in test tenant |
| `test_product` | function | `Product` in test tenant |
| `test_model` | function | `Model` (3D file) in test tenant |
| `test_printer` | function | `Printer` in test tenant |
| `seed_material_types` | function | Seeds PLA, PETG, ABS, TPU, etc. |
| `s3_mock` | function | `moto` S3 mock with test bucket |
| `image_storage_fixture` | function | Storage configured by `TEST_STORAGE_TYPE` env var |
| `auth_headers` | function | Mock JWT headers dict |

**Per-test-file fixtures** follow the same `@pytest_asyncio.fixture` pattern as conftest, but scoped to the file (e.g., `second_spool`, `inactive_spool` in `test_spools.py`).

**Factory functions** used instead of fixtures when uniqueness is needed per call:
```python
def create_payment_request(payment_token="cnon:card-nonce-ok", amount=2999, ...) -> PaymentRequest:
    """Create a test payment request."""
    return PaymentRequest(...)
```

## Frontend Test File Organization

**Location:**
- Co-located with source — test files sit next to the files they test
- `src/components/<module>/<Component>.test.tsx`
- `src/hooks/<hookName>.test.ts`
- `src/lib/<module>.test.ts` and `src/lib/api/<resource>.test.ts`
- Shared utilities in `src/test/test-utils.tsx` and `src/test/setup.ts`

**Structure:**
```
frontend/src/
├── test/
│   ├── setup.ts                   # Global test setup (mocks, cleanup)
│   └── test-utils.tsx             # render(), createWrapper(), createTestQueryClient()
├── components/
│   └── inventory/
│       ├── SpoolList.tsx
│       └── SpoolList.test.tsx     # Co-located test
├── hooks/
│   ├── useModules.ts
│   └── useModules.test.ts
└── lib/
    ├── api.ts
    ├── api.test.ts
    └── api/
        ├── sku.ts
        └── sku.test.ts
```

## Frontend Test Structure

**Component Tests:**
```typescript
import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// 1. Mock external dependencies
vi.mock('@/lib/api/spools', () => ({
  spoolsApi: { list: vi.fn() },
}))
const mockSpoolsApiList = spoolsApi.list as Mock

// 2. Inline mock data
const mockSpools: Spool[] = [{ id: '1', spool_id: 'FIL-001', ... }]

// 3. Test QueryClient wrapper
function renderWithQueryClient(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>)
}

describe('SpoolList', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders loading state initially', () => {
    mockSpoolsApiList.mockReturnValue(new Promise(() => {}))
    renderWithQueryClient(<SpoolList />)
    expect(screen.getByText(/Loading spools/i)).toBeInTheDocument()
  })
})
```

**Hook Tests** (use `renderHook` + `createWrapper` from `src/test/test-utils.tsx`):
```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { createWrapper } from '@/test/test-utils'

vi.mock('@/lib/api/modules', () => ({ getModules: vi.fn() }))
const mockGetModules = vi.mocked(getModules)

it('fetches modules successfully', async () => {
  mockGetModules.mockResolvedValue(mockModulesResponse)
  const { result } = renderHook(() => useModules(), { wrapper: createWrapper() })
  await waitFor(() => expect(result.current.isLoading).toBe(false))
  expect(result.current.data).toEqual(mockModulesResponse)
})
```

## Frontend Global Setup Mocks

Configured in `frontend/src/test/setup.ts`:
- `@tanstack/react-router` — mocked globally (Link, useNavigate, useRouter, useRouterState)
- `window.matchMedia` — mocked
- `IntersectionObserver` — mocked
- `ResizeObserver` — mocked
- `Element.prototype.scrollIntoView` — mocked
- Radix UI pointer capture APIs — mocked
- `crypto.randomUUID` — mocked with `Math.random()`
- `afterEach(() => cleanup())` — auto-cleanup after each test

## E2E Tests (Playwright)

**Framework:** Playwright
**Config:** `frontend/playwright.config.ts`
**Test directory:** `frontend/e2e/`
**Browsers:** Chromium, Firefox, WebKit

**Structure:**
```
frontend/e2e/
├── helpers.ts               # isBackendAvailable(), registerAndLogin()
├── config.ts                # Base URL, timeouts
├── tests/
│   ├── auth/                # login.spec.ts, registration.spec.ts
│   ├── inventory/           # spools.spec.ts, spool-fields.spec.ts
│   ├── products/            # product-crud.spec.ts, product-fields.spec.ts
│   ├── settings/            # settings-workflow.spec.ts
│   └── ...
```

**Configuration:**
- `baseURL`: defaults to `https://www.batchivo.com`, override with `PLAYWRIGHT_BASE_URL` env var
- Workers: 1 (serial) to prevent registration rate-limiting conflicts
- Retries: 2 on CI, 1 locally
- Screenshots on failure, traces on first retry

**E2E Pattern:**
```typescript
import { test, expect } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

test.beforeEach(async ({ page }) => {
  // Skip if backend unavailable
  const available = await isBackendAvailable()
  test.skip(!available, 'Backend not available')
  await registerAndLogin(page)
})
```

## Coverage

**Backend:**
- Tool: `pytest-cov` with `coverage.xml` output
- Run: `poetry run pytest --cov=app --cov-report=term-missing`
- No minimum threshold enforced in config (CI uses coverage report)

**Frontend:**
- Provider: `v8`
- Minimum thresholds: 30% statements, branches, functions, lines (enforced by vitest)
- Excludes: `node_modules/`, `src/test/`, `**/*.d.ts`, `**/*.config.*`, `src/main.tsx`
- Reports: `text`, `html`, `lcov`

## Test Types Summary

**Backend Unit Tests** (`tests/unit/`):
- Test service classes directly against real async DB session
- Test Pydantic schema validation (no DB required)
- Test standalone utilities (SKU generator, slugify, security tokens)
- Use `@pytest_asyncio.fixture` for DB setup, no HTTP client

**Backend Integration Tests** (`tests/integration/`):
- Test HTTP endpoints via `unauthenticated_client` (no auth bypass)
- Validate real auth flows, JWT validation, error responses
- Use actual login flow to get tokens

**Backend API Tests** (`tests/api/`):
- Test HTTP endpoints via `client` (with auth bypassed via dependency overrides)
- Cover: success (200/201), auth (401), validation (422), not-found (404)
- May use both `client` and `unauthenticated_client` in same file

**Frontend Unit Tests** (co-located `.test.tsx/.ts`):
- Component rendering and interaction
- Hook behavior with mocked API
- Utility function logic
- Library wrapper behavior (api client, auth utilities)

**Frontend E2E Tests** (`e2e/`):
- Full user workflows against running stack
- Form submission, CRUD operations, navigation

---

*Testing analysis: 2026-05-19*
