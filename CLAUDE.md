# Batchivo - 3D Print Business Management Platform

## Critical Rules (MANDATORY)

### Deployment
**Only workflow for deploying changes:**
1. Push to GitHub (main branch)
2. Woodpecker CI builds Docker images → pushes to k3s registry
3. ArgoCD auto-syncs within 3 minutes

**NEVER manually build/push Docker images. NEVER `kubectl apply` directly.**

- **CI**: https://ci.techize.co.uk (Woodpecker)
- **CD**: https://argocd.techize.co.uk (ArgoCD)
- **Registry**: `192.168.98.138:30500`

### Branch & Commit
- Direct to main (current strategy)
- Commit style: `type: description` (e.g., `fix:`, `feat:`, `docs:`)
- No AI markers or Co-Authored-By in commits

### Code Quality
- **All code MUST have tests** — no exceptions
- Before committing: `cd backend && poetry run pytest && poetry run ruff check`
- Frontend: `cd frontend && npm test && npm run lint`

### Multi-Tenant Security
- Every table has `tenant_id` — **NEVER** query without tenant scope
- Use `get_current_tenant()` dependency in all endpoints
- PostgreSQL RLS enforces isolation at database level

```python
@router.get("/items")
async def list_items(
    tenant: Tenant = Depends(get_current_tenant),  # REQUIRED
    db: AsyncSession = Depends(get_db)
):
    pass  # Queries auto-scoped via RLS
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Backend dev | `cd backend && poetry run uvicorn app.main:app --reload` |
| Frontend dev | `cd frontend && npm run dev` |
| Run tests | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| Lint | `cd backend && poetry run ruff check && poetry run ruff format --check` |
| DB migrate | `cd backend && poetry run alembic upgrade head` |
| New migration | `cd backend && poetry run alembic revision --autogenerate -m "description"` |

| Production | Command |
|------------|---------|
| Check pods | `kubectl get pods -n batchivo` |
| Backend logs | `kubectl logs -l app=backend -n batchivo -f` |
| Frontend logs | `kubectl logs -l app=frontend -n batchivo -f` |
| ArgoCD sync | `argocd app sync batchivo-app` |
| Rollback | `argocd app rollback batchivo-app` |
| Verify health | `curl https://api.batchivo.com/health` |

---

## Architecture

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL | React 18 + TypeScript + TanStack Query + shadcn/ui | k3s + ArgoCD + Cloudflare Tunnel | Custom JWT auth

**URLs:**
- Admin/API: www.batchivo.com / api.batchivo.com
- Shop: test.mystmereforge.co.uk → mystmereforge-shop repo

---

## Testing Policy

| Change Type | Required Tests |
|-------------|----------------|
| New endpoint | Success (200/201), auth (401), validation (422), not found (404) |
| Business logic | Success path, edge cases, error conditions |
| Bug fix | Regression test proving fix works |
| Schema change | Model CRUD, relationships, constraints |

**Available fixtures:** `client`, `db_session`, `test_tenant`, `test_user`, `test_spool`

---

## Integrations

### Square (Payments)
- Secret: `kubectl get secret square-credentials -n batchivo`
- Webhook: `https://api.batchivo.com/api/v1/payments/webhooks/square`
- Events: `payment.created`, `payment.updated`, `refund.created`, `refund.updated`
- Status: sandbox credentials active — switch to production when ready

### Resend (Email)
- Secret: `kubectl get secret resend-credentials -n batchivo`
- From: orders@mystmereforge.co.uk
- Service: `backend/app/services/email_service.py`
- Status: production credentials active, sends order confirmation emails

---

## Troubleshooting

```bash
# Pod not starting
kubectl describe pod <pod-name> -n batchivo
kubectl logs <pod-name> -n batchivo --previous

# Database shell
kubectl exec -it postgres-0 -n batchivo -- psql -U batchivo -d batchivo

# ArgoCD out of sync
argocd app sync batchivo-app --prune
```

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Batchivo — Filament Inventory Refinement**

A focused refinement of Batchivo's filament tracking system. The current system has two duplicate routes (`/inventory` and `/filaments`) pointing at the same page, and a data model that conflates filament type definitions with individual physical spools. This project restructures the data model, consolidates the UI, and introduces frictionless workflows for bulk filament entry and label printing.

**Core Value:** Every spool in the physical collection has a record in the system, a label, and a known status — with minimal effort to get it there.

### Constraints

- **Tech Stack**: FastAPI + SQLAlchemy (async) + PostgreSQL — no framework changes
- **Migration Safety**: ~90 existing migrations in place; new migration must preserve existing spool data
- **Multi-Tenant**: All new models must include `tenant_id` with RLS enforcement
- **No Breaking Changes**: Existing production routes and API endpoints must remain functional during migration
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Backend API (`backend/`)
- TypeScript 5.9 - Frontend SPA (`frontend/`) and docs site (`docs-site/`)
- TypeScript 5.x - Landing page (`landing/`)
- YAML - Infrastructure as code (`infrastructure/`)
## Runtime
- CPython 3.12 (Alpine Linux in Docker)
- Constraint: `requires-python = ">=3.12,<4.0"` in `backend/pyproject.toml`
- Node.js (version not pinned via `.nvmrc` — check `frontend/Dockerfile` for exact version)
## Package Managers
- Poetry >=2.0.0 (PEP 621 with `pyproject.toml`)
- Lockfile: `backend/poetry.lock` (present)
- Alt npm lockfile present at `backend/package-lock.json` (legacy artifact)
- pnpm (primary — `frontend/pnpm-lock.yaml` present)
- npm lockfile also present (`frontend/package-lock.json`) — pnpm is canonical
- Landing page: npm (`landing/package-lock.json`)
- Docs site: npm (`docs-site/package-lock.json`)
## Frameworks
- FastAPI >=0.124.4 — REST API framework (`backend/app/main.py`)
- SQLAlchemy 2.0 (async) — ORM (`backend/app/database.py`, `backend/app/models/`)
- Alembic >=1.13.0 — Database migrations (`backend/alembic/`)
- Pydantic v2 + pydantic-settings — Settings and schema validation (`backend/app/config.py`, `backend/app/schemas/`)
- Starlette 0.49.3 (pinned) — ASGI foundation under FastAPI
- React 19.2 — UI framework (`frontend/src/`)
- Vite 7.x — Build tool and dev server (`frontend/vite.config.ts`)
- TanStack Router 1.141 — File-based routing (`frontend/src/routes/`)
- TanStack Query 5.90 — Server state / data fetching (`frontend/src/`)
- shadcn/ui — Component library built on Radix UI (`frontend/src/components/`)
- Tailwind CSS 3.4 — Utility-first styling
- Zod 4.x — Schema validation on frontend
- react-hook-form 7.x — Form management
- Next.js 16.2 — Static/SSR marketing site (`landing/`)
- Tailwind CSS 4 — Styling
- Docusaurus 3.9.2 — Documentation site (`docs-site/`)
- Celery >=5.3.0 with Redis broker — Async task queue (configured in `backend/app/config.py`, broker: `redis://localhost:6379/1`)
- Uvicorn[standard] >=0.38.0 — ASGI server
## Key Dependencies
- `psycopg[binary,pool]` >=3.1.0 — PostgreSQL async driver (`backend/`)
- `asyncpg` >=0.31.0 — Additional async PostgreSQL driver
- `redis` >=5.0.0 — Redis client for caching and Celery
- `PyJWT` >=2.12.0 — Custom JWT authentication (`backend/app/core/security.py`)
- `bcrypt` >=4.0.0 — Password hashing (`backend/app/auth/password.py`)
- `authlib` >=1.6.9 — OAuth2 client support
- `httpx` >=0.26.0 — Async HTTP client for external service calls
- `slowapi` >=0.1.9 — Rate limiting middleware (`backend/app/core/rate_limit.py`)
- `squareup` >=42.0.0 — Square Payments SDK (`backend/app/services/square_payment.py`)
- `etsyv3` >=0.0.7 — Etsy API SDK (`backend/app/services/etsy_sync.py`)
- `boto3` >=1.35.0 — AWS/MinIO S3 SDK (`backend/app/services/image_storage.py`)
- `paho-mqtt` >=2.1.0 — MQTT for Bambu Lab printer communication (`backend/app/services/bambu_mqtt.py`)
- `qrcode[pil]` >=7.4.0 — QR code generation (`backend/app/`)
- `pillow` >=12.2.0 — Image processing
- `opentelemetry-api/sdk` >=1.27.0 — Backend tracing and metrics
- `opentelemetry-exporter-otlp` >=1.27.0 — Exports to Tempo (OTLP)
- `opentelemetry-exporter-prometheus` >=0.48b0 — Prometheus metrics endpoint
- `sentry-sdk[fastapi]` >=2.0.0 — Error tracking (`backend/app/observability/sentry.py`)
- `@sentry/react` >=8.0.0 — Frontend error tracking (`frontend/src/lib/sentry.ts`)
- `@opentelemetry/*` — Frontend distributed tracing (`frontend/src/lib/telemetry.ts`)
- `pytest` >=9.0.3 + `pytest-asyncio` >=1.3.0 + `pytest-cov` >=4.1.0
- `fakeredis` >=2.32.1 — Redis mocking
- `moto[s3]` >=5.0.0 — AWS S3 mocking
- `respx` >=0.21.0 — httpx request mocking
- `pytest-xdist` >=3.8.0 — Parallel test execution
- Vitest 4.x — Unit/component test runner
- Playwright 1.59 — E2E tests (`frontend/src/test/`)
- `@testing-library/react` 16.x + `@testing-library/user-event`
- Storybook 10.x — Component development and visual testing
## Configuration
- Config: `backend/app/config.py` — `pydantic-settings` reads from `.env` + environment variables
- Required: `SECRET_KEY` (no default — enforced by validator)
- Key groups: database, Redis, CORS, OpenTelemetry, Celery, storage (local/S3), Square, Shopify, Brevo email, Sentry
- `frontend/src/lib/config.ts` — reads from `window.__RUNTIME_CONFIG__` (set at container startup) with fallback to `import.meta.env`
- Allows runtime injection without rebuilding images
- Key vars: `VITE_API_URL`, `VITE_OTEL_ENDPOINT`, `VITE_SENTRY_DSN`, `VITE_BUILD_SHA`
- `frontend/vite.config.ts` — code splitting, proxy rules, Sentry source map upload
- `backend/pyproject.toml` — `[tool.ruff]`, `[tool.black]`, `[tool.mypy]`, `[tool.pytest.ini_options]`
- `frontend/tsconfig.json` — TypeScript strict mode, path alias `@` → `./src`
## Platform Requirements
- Python 3.12+
- Node.js (recent LTS)
- PostgreSQL 16 (or Docker)
- Redis 7 (or Docker)
- Docker Compose: `docker-compose.yml` at repo root
- k3s Kubernetes cluster (`infrastructure/k8s/`)
- Cloudflare Tunnel for ingress (`infrastructure/cloudflare/`)
- Self-hosted container registry: `registry.techize.co.uk`
- CI: Woodpecker CI at `https://ci.techize.co.uk`
- CD: ArgoCD at `https://argocd.techize.co.uk`
- Docker images: Python 3.12-Alpine (backend), Node Alpine (frontend)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python modules: `snake_case.py` (e.g., `production_run.py`, `image_storage.py`)
- Python test files: `test_<module_name>.py` (e.g., `test_production_run_service.py`)
- TypeScript components: `PascalCase.tsx` (e.g., `SpoolList.tsx`, `CreateRunWizard.tsx`)
- TypeScript test files: `<ComponentName>.test.tsx` or `<hookName>.test.ts` (co-located)
- TypeScript hooks: `use<Name>.ts` (e.g., `useModules.ts`, `useSKU.ts`)
- TypeScript API modules: `<resource>.ts` under `src/lib/api/`
- TypeScript type definitions: `<resource>.ts` under `src/types/`
- Python: `snake_case` (e.g., `create_production_run`, `ensure_material_type_exists`)
- TypeScript: `camelCase` (e.g., `createTestQueryClient`, `renderWithQueryClient`)
- React components: `PascalCase`
- React hooks: `use<Name>` prefix enforced by ESLint
- Python: `snake_case`
- TypeScript: `camelCase` for variables, `UPPER_SNAKE_CASE` for constants (e.g., `TEST_S3_BUCKET`, `SQUARE_ERROR_MESSAGES`)
- Python: `PascalCase` classes (e.g., `SpoolCreate`, `SpoolResponse`, `ProductionRunService`)
- TypeScript interfaces: `PascalCase` with descriptive suffix — `interface SpoolBase`, `interface SpoolListResponse`, `interface SpoolListParams`
- Pydantic schemas follow Base/Create/Update/Response naming pattern
## Code Style
- Tool: `black` + `ruff`
- Line length: 100 characters
- Target: Python 3.11+
- Config: `backend/pyproject.toml`
- Tool: `ruff`
- Ignored rules: `F821` (SQLAlchemy string annotations), `E402` (conditional imports)
- Type checking: `mypy` with `disallow_untyped_defs = true`
- Tool: TypeScript ESLint (`typescript-eslint`)
- Config: `frontend/eslint.config.js`
- Rules: `react-hooks/rules-of-hooks` (error), `react-hooks/exhaustive-deps` (warn)
## Import Organization
- `@` → `src/`
## Error Handling
- HTTP errors: `raise HTTPException(status_code=status.HTTP_4XX_..., detail="message")`
- Database integrity errors: catch `IntegrityError`, rollback, then raise `HTTPException(400)`
- Validation errors handled automatically by Pydantic/FastAPI (returns 422)
- Service errors: log with `logger.error()` then re-raise or rollback
- Auth errors: raise `HTTPException(status_code=401/403)`
- Axios interceptor handles 401 → auto token refresh → redirect to `/login`
- TanStack Query handles retry logic (disabled in tests)
- API errors bubble up through React Query's `error` state
## Logging
- Module-level logger: `logger = logging.getLogger(__name__)` at top of each file
- Info for successful state changes: `logger.info(f"Completed production run {run_id}")`
- Warning for non-critical failures: `logger.warning(f"Failed to record metrics: {e}")`
- Error for rollback/failure scenarios: `logger.error(f"Failed to complete production run {run_id}, rolled back: {e}")`
- f-strings used throughout for log message formatting
## Comments
- Module docstrings required: `"""Spool inventory API endpoints."""`
- Class docstrings required with description of purpose
- Function docstrings: used on fixtures and complex functions
- Inline comments for non-obvious logic, tenant isolation, and security decisions
- Section dividers used in test files: `# ============================================`
## Function Design
- Async functions for all database operations and API endpoints
- Service methods accept `db: AsyncSession` and `tenant: Tenant` as first parameters
- Dependencies injected via FastAPI `Depends()` — not passed directly
- Functions under ~50 lines; complex orchestration split to service classes
- Hooks return destructured named properties (not raw query objects)
- Components receive typed props interfaces
## Module Design
- Services are classes instantiated per-request: `ProductionRunService(db, tenant, user=None)`
- Located in `backend/app/services/`
- Methods are `async def` throughout
- Pydantic v2 with `ConfigDict` and `model_dump()`
- Base → Create → Update → Response inheritance hierarchy
- Field validation uses `Field(..., min_length=1, description="...")`
- API functions grouped by resource in `src/lib/api/<resource>.ts`
- Hooks wrap API functions with TanStack Query in `src/hooks/use<Name>.ts`
- Types mirroring backend Pydantic schemas in `src/types/<resource>.ts`
## Multi-Tenant Security Convention
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
```
## Component Responsibilities
| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| FastAPI App | Entry point, middleware chain, router registration | `backend/app/main.py` |
| Auth Layer | JWT validation, tenant resolution, RLS context, roles | `backend/app/auth/dependencies.py`, `backend/app/auth/middleware.py` |
| API Routes (v1) | HTTP handlers, validation, response mapping | `backend/app/api/v1/*.py` |
| Services | Business logic, external integrations, complex operations | `backend/app/services/*.py` |
| Models | SQLAlchemy ORM models with UUID PKs and tenant_id FK | `backend/app/models/*.py` |
| Schemas | Pydantic request/response validation | `backend/app/schemas/*.py` |
| Feature Modules | Pluggable domain modules (3D print, knitting) with route registration | `backend/app/modules/` |
| Observability | Sentry error tracking, OpenTelemetry tracing + metrics | `backend/app/observability/` |
| Frontend SPA | React 18 app, TanStack Router, TanStack Query, shadcn/ui | `frontend/src/` |
| API Client | Typed axios wrapper with JWT interceptor + refresh | `frontend/src/lib/api.ts`, `frontend/src/lib/api/*.ts` |
| Auth Context | React auth state, token management, session persistence | `frontend/src/contexts/AuthContext.tsx` |
## Pattern Overview
- Every database table carries `tenant_id`; RLS policies enforce isolation at the PostgreSQL layer
- Feature modules (3D printing, knitting) are enabled/disabled per-tenant type; module system uses `BaseModule` abstract class in `backend/app/modules/base.py`
- API routes are thin — business logic lives in dedicated service classes under `backend/app/services/`
- Frontend uses TanStack Query for server state; `ModuleGuard` components protect module-gated routes
- Two separate auth flows: internal users (JWT) and storefront customers (`customer_auth` / `customer_dependencies`)
## Layers
- Purpose: Cross-cutting concerns applied before route handlers
- Location: `backend/app/middleware/`, `backend/app/auth/middleware.py`
- Contains: `TenantContextMiddleware` (extracts tenant_id from JWT → `request.state.tenant_id`), `SecurityHeadersMiddleware`, `MetricsMiddleware`, `CORSPreflightMiddleware`
- Depends on: `backend/app/core/security.py` (JWT decode)
- Used by: All requests
- Purpose: FastAPI dependencies that validate tokens, resolve tenants, set RLS context
- Location: `backend/app/auth/dependencies.py`
- Contains: `get_current_user`, `get_current_tenant`, `get_tenant_db` (sets `SET LOCAL app.current_tenant_id`), `get_shop_tenant`, `get_platform_admin`, role hierarchy checking
- Depends on: Models, core/security
- Used by: All protected route handlers
- Purpose: Route handlers — validate input, call services or direct DB queries, return schemas
- Location: `backend/app/api/v1/`
- Contains: ~45 router modules (spools, models, products, orders, payments, printers, shop, platform, etc.)
- Depends on: Auth dependencies, services, models, schemas
- Used by: FastAPI router registration in `main.py`
- Purpose: Encapsulates business logic that is too complex for route handlers
- Location: `backend/app/services/`
- Contains: `ProductionRunService`, `PrintQueueService`, `EmailService`, `SquarePaymentService`, `ShopifySyncService`, `EtsySyncService`, `ImageStorageService`, `InventoryTransactionService`, `ForecastingService`, etc.
- Pattern: Service classes instantiated with `(db, tenant, user)` constructor; stateless helpers as module-level functions
- Depends on: Models, schemas, external clients
- Used by: API route handlers
- Purpose: Pluggable feature groupings enabled per tenant type
- Location: `backend/app/modules/`
- Contains: `BaseModule` ABC (`modules/base.py`), module registry (`modules/registry.py`), `threed_print/` (categories, consumables, designers, models, orders, printers, production, products, sales_channels, spools), `knitting/` (needle, pattern, project, yarn)
- Depends on: API routes it wraps
- Used by: `backend/app/api/v1/modules.py` (module info endpoint), tenant module access control
- Purpose: Database models and schema definitions
- Location: `backend/app/models/`, `backend/app/schemas/`
- Contains: 40+ SQLAlchemy models using `UUIDMixin` + `TimestampMixin` from `models/base.py`, corresponding Pydantic schemas
- Pattern: Models inherit `Base, UUIDMixin, TimestampMixin`; all tenant-scoped models have `tenant_id` column
- Depends on: `backend/app/database.py` for `Base`
- Used by: Services, route handlers
- Purpose: React SPA for the management console
- Location: `frontend/src/`
- Contains: Pages, feature components, API clients, auth context, hooks, guards
- Pattern: TanStack Query for server state caching; typed API clients per resource in `lib/api/*.ts`; `ModuleGuard` wraps module-gated routes; `PlatformAdminGuard` protects platform admin pages
## Data Flow
### Authenticated API Request
### Public Storefront Request
### WebSocket (Printer Monitoring)
### Token Refresh Flow
- Server state: TanStack Query (`@tanstack/react-query`) with 1 retry, no window-focus refetch
- Auth state: `AuthContext` in `frontend/src/contexts/AuthContext.tsx`
- Offline spools: IndexedDB via `frontend/src/lib/db/indexeddb.ts` + `frontend/src/hooks/useOfflineSpools.ts`
## Key Abstractions
- Purpose: Abstract base for all pluggable feature modules
- File: `backend/app/modules/base.py`
- Pattern: Subclasses set `name`, `display_name`, `tenant_types`, `is_core`; implement `register_routes(router)`. `is_enabled_for_tenant(tenant)` checks `tenant.tenant_type` against `tenant_types` list.
- Purpose: Uniform interface for multiple printer hardware types
- File: `backend/app/services/printer_adapter.py`
- Pattern: Python `Protocol` (structural subtyping) — Bambu (`bambu_mqtt.py`) and Moonraker (`moonraker_adapter.py`) both satisfy without explicit inheritance
- Purpose: Clean dependency injection into route handlers
- File: `backend/app/auth/dependencies.py` (lines 219–296)
- Pattern: `CurrentUser = Annotated[User, Depends(get_current_user)]` — used as parameter type hints in route functions
- Purpose: Typed resource-specific API clients using shared axios instance
- File: `frontend/src/lib/api.ts` (base client), `frontend/src/lib/api/*.ts` (resource clients)
- Pattern: Each resource file exports an object (`spoolsApi`, `modelsApi`, etc.) with typed async methods that call `apiClient.get/post/put/delete`
## Entry Points
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app` or Kubernetes deployment
- Responsibilities: Creates FastAPI app, registers middleware (order matters), mounts all API routers, serves static images
- Location: `frontend/src/main.tsx`
- Triggers: Browser load / Vite dev server / Docker+nginx
- Responsibilities: Initialises Sentry, optional OpenTelemetry, wraps app in `ErrorBoundary`, renders `App`
- Location: `frontend/src/App.tsx`
- Responsibilities: Defines full route tree (TanStack Router), wraps routes in `ProtectedRoute`, `ModuleGuard`, or `PlatformAdminGuard` as required, provides `QueryClientProvider`
## Architectural Constraints
- **Threading:** FastAPI async (asyncio single-threaded event loop). All DB operations are async via `sqlalchemy.ext.asyncio`. WebSocket connections handled in same event loop.
- **Global state:** `engine` and `async_session_maker` are module-level singletons in `backend/app/database.py`. Settings cached with `@lru_cache` in `backend/app/config.py`.
- **RLS toggle:** `settings.rls_enabled` (default `False` in dev, `True` in production). When disabled, tenant isolation relies on application-level `tenant_id` filtering. `get_tenant_db` dependency is required (not `get_db`) for RLS to function.
- **Module gating (frontend):** `ModuleGuard` calls `useRouteAccess` hook (`frontend/src/hooks/useModules.ts`), which queries `/api/v1/modules` to check if the current tenant has the feature enabled.
- **Circular imports:** Module system defers router imports inside `register_routes` to avoid circular import at startup (see `backend/app/modules/base.py:54`).
## Anti-Patterns
### Direct DB Queries in Route Handlers Without Service Layer
### `get_db` Used Instead of `get_tenant_db` for Tenant-Scoped Data
## Error Handling
- Auth failures → `HTTP 401` with `WWW-Authenticate: Bearer` header
- Permission failures → `HTTP 403`
- Not found → `HTTP 404`
- Validation failures → `HTTP 422` (automatic from Pydantic)
- Database errors → rolled back automatically in `get_db` / `get_tenant_db` session context managers
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
