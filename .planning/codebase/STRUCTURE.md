# Codebase Structure

**Analysis Date:** 2026-05-19

## Directory Layout

```
batchivo/                          # Repository root
├── backend/                       # FastAPI Python backend
│   ├── app/                       # Application source
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── config.py              # Pydantic settings (env vars)
│   │   ├── database.py            # SQLAlchemy engine, session, Base
│   │   ├── api/
│   │   │   └── v1/                # All REST route handlers (~45 modules)
│   │   ├── auth/                  # Auth dependencies and middleware
│   │   │   ├── dependencies.py    # get_current_user, get_current_tenant, TenantDB, etc.
│   │   │   ├── middleware.py      # TenantContextMiddleware
│   │   │   ├── customer_dependencies.py  # Public storefront auth
│   │   │   └── password.py        # Bcrypt helpers
│   │   ├── core/                  # Low-level utilities
│   │   │   ├── security.py        # JWT create/decode
│   │   │   ├── encryption.py      # Field encryption helpers
│   │   │   └── rate_limit.py      # SlowAPI limiter config
│   │   ├── middleware/            # Starlette middleware classes
│   │   │   ├── security.py        # SecurityHeadersMiddleware
│   │   │   └── metrics.py         # MetricsMiddleware (OTel)
│   │   ├── models/                # SQLAlchemy ORM models (40+)
│   │   │   └── base.py            # UUIDMixin, TimestampMixin
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/              # Business logic services
│   │   ├── modules/               # Pluggable feature modules
│   │   │   ├── base.py            # BaseModule ABC, ModuleInfo, RouteInfo
│   │   │   ├── registry.py        # Module registry
│   │   │   ├── threed_print/      # 3D printing module (10 sub-modules)
│   │   │   └── knitting/          # Knitting module (yarn, needle, pattern, project)
│   │   ├── observability/         # Sentry, OpenTelemetry (traces + metrics)
│   │   └── utils/                 # Shared utilities (csv_handler, etc.)
│   ├── alembic/                   # Database migrations (90 versions)
│   │   └── versions/
│   └── tests/                     # Test suite
│       ├── api/                   # API (integration-style) tests
│       ├── unit/                  # Unit tests
│       ├── integration/           # Integration tests
│       └── utils/                 # Test fixtures and helpers
├── frontend/                      # React 18 TypeScript SPA
│   └── src/
│       ├── main.tsx               # React entry point (Sentry, OTel init)
│       ├── App.tsx                # Route tree definition (TanStack Router)
│       ├── components/            # Reusable UI components
│       │   ├── ui/                # shadcn/ui primitives
│       │   ├── guards/            # ModuleGuard, PlatformAdminGuard
│       │   ├── layout/            # Navigation, sidebar, shell
│       │   ├── dashboard/         # Dashboard widgets
│       │   ├── inventory/         # Spool inventory components
│       │   ├── models/            # Model catalog components
│       │   ├── products/          # Product management + ProductWizard
│       │   ├── orders/            # Order management components
│       │   ├── printers/          # Printer management components
│       │   ├── production-runs/   # Production run components
│       │   ├── sales-channels/    # Sales channel components
│       │   ├── onboarding/        # Onboarding wizard components
│       │   ├── platform/          # Platform admin components
│       │   ├── categories/        # Category management
│       │   ├── designers/         # Designer management
│       │   └── charts/            # Analytics charts
│       ├── pages/                 # Page-level components (one per route)
│       │   ├── knitting/          # Knitting module pages
│       │   ├── platform/          # Platform admin pages
│       │   └── help/              # Help center pages
│       ├── contexts/              # React contexts
│       │   └── AuthContext.tsx    # Auth state provider
│       ├── hooks/                 # Custom React hooks
│       ├── lib/                   # Shared libraries
│       │   ├── api.ts             # Axios instance + interceptors
│       │   ├── api/               # Per-resource typed API clients
│       │   ├── auth.ts            # Token storage/validation helpers
│       │   ├── config.ts          # Runtime config (API URL)
│       │   ├── db/                # IndexedDB (offline spools)
│       │   │   └── indexeddb.ts
│       │   ├── sentry.ts          # Sentry frontend init
│       │   └── telemetry.ts       # OpenTelemetry frontend init
│       ├── routes/                # Route config helpers
│       ├── types/                 # TypeScript type definitions
│       ├── utils/                 # Shared utility functions
│       └── content/
│           └── guides/            # Help center MDX/markdown content
├── infrastructure/                # Kubernetes and deployment config
│   ├── k8s/                       # K8s manifests (namespace, backend, frontend,
│   │   │                          #   postgres, redis, minio, ingress, network-policies)
│   │   └── argocd/ (via root)
│   ├── argocd/
│   │   └── application.yaml       # ArgoCD app definition
│   └── cloudflare/                # Cloudflare Tunnel setup docs
├── landing/                       # Next.js marketing/landing site (separate app)
├── docs/                          # Internal docs
├── docs-site/                     # Documentation site
├── scripts/                       # Utility scripts
├── .woodpecker/                   # Woodpecker CI pipeline definitions
│   ├── build.yml                  # Docker build + push to registry
│   ├── test-fast.yml              # Fast test gate
│   └── test-integration.yml       # Integration test gate
├── docker-compose.yml             # Local dev environment
├── Makefile                       # Dev task shortcuts
└── CLAUDE.md                      # Project conventions and quick reference
```

## Directory Purposes

**`backend/app/api/v1/`:**
- Purpose: All HTTP route handlers, registered in `main.py`
- Contains: One file per resource group (spools, models, products, orders, payments, printers, shop, platform, etc.) plus websocket (`printer_ws.py`) and test utility (`test.py`, disabled in production)
- Key files: `auth.py`, `spools.py`, `products.py`, `orders.py`, `payments.py`, `printer_ws.py`, `shop.py`, `platform.py`

**`backend/app/auth/`:**
- Purpose: Authentication and authorisation primitives
- Key files: `dependencies.py` (all FastAPI auth dependencies), `middleware.py` (tenant context extraction), `customer_dependencies.py` (public shop auth)

**`backend/app/services/`:**
- Purpose: Business logic that routes delegate to
- Key files: `production_run.py`, `print_queue_service.py`, `square_payment.py`, `email_service.py`, `image_storage.py`, `shopify_sync.py`, `etsy_sync.py`, `bambu_mqtt.py`, `printer_adapter.py`, `forecasting_service.py`, `audit_service.py`, `cache_service.py`

**`backend/app/modules/`:**
- Purpose: Per-tenant-type feature groupings using `BaseModule` ABC
- Key files: `base.py` (abstract base), `registry.py` (module registry), `threed_print/` (10 sub-modules), `knitting/` (4 sub-modules)

**`backend/app/models/`:**
- Purpose: SQLAlchemy 2.0 ORM models. Every tenant-scoped table has `tenant_id UUID NOT NULL`
- Key files: `base.py` (mixins), `tenant.py`, `user.py`, `spool.py`, `product.py`, `order.py`, `production_run.py`, `printer.py`

**`backend/alembic/versions/`:**
- Purpose: Database migration history (90 migration files as of analysis date)
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes

**`frontend/src/lib/api/`:**
- Purpose: One typed API client module per backend resource
- Key files: `spools.ts`, `products.ts`, `models.ts`, `orders.ts`, `printers.ts`, `production-runs.ts`, `sales-channels.ts`, `categories.ts`, `settings.ts`

**`frontend/src/components/guards/`:**
- Purpose: Route protection components
- Key files: `ModuleGuard.tsx` (checks tenant module access via `useModules` hook), `PlatformAdminGuard.tsx` (checks `user.is_platform_admin`)

**`infrastructure/k8s/`:**
- Purpose: Kubernetes manifests for k3s cluster deployment
- Contains: Separate subdirs per service (backend, frontend, postgres, redis, minio, ingress, network-policies, cloudflare-tunnel, buildkitd)
- Committed: Yes (secrets use `.template` suffixed files; actual secrets applied separately)

**`landing/`:**
- Purpose: Separate Next.js marketing site, independent from the main React SPA
- Generated: No (committed Next.js app)

## Naming Conventions

**Files (Backend):**
- Route handlers: `snake_case.py` matching resource name (e.g., `production_runs.py`, `sales_channels.py`)
- Services: `snake_case_service.py` or `snake_case.py` (e.g., `print_queue_service.py`, `production_run.py`)
- Models: singular `snake_case.py` (e.g., `product.py`, `production_run.py`)
- Schemas: singular `snake_case.py` mirroring model name (e.g., `production_run.py`)
- Migrations: auto-generated `{revision}_{slug}.py`

**Files (Frontend):**
- Pages: `PascalCase.tsx` (e.g., `ProductDetailPage.tsx`, `DashboardHome.tsx`)
- Components: `PascalCase.tsx` (e.g., `ModuleGuard.tsx`)
- API clients: `kebab-case.ts` (e.g., `production-runs.ts`, `sales-channels.ts`)
- Hooks: `useCamelCase.ts` (e.g., `useModules.ts`, `useOfflineSpools.ts`)
- Types: `camelCase.ts` or matching resource (e.g., `spool.ts`)

**Directories:**
- Backend: `snake_case/`
- Frontend components/pages: `kebab-case/` (e.g., `production-runs/`, `sales-channels/`)
- Frontend lib/hooks: flat, no subdirectories except `api/` and `db/`

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app creation, middleware stack, all router registration
- `frontend/src/main.tsx`: React bootstrap, Sentry/OTel init
- `frontend/src/App.tsx`: Complete route tree, auth wrapping

**Configuration:**
- `backend/app/config.py`: All env-var driven settings via Pydantic `Settings` class
- `frontend/src/lib/config.ts`: Frontend runtime config (API URL, feature flags)
- `docker-compose.yml`: Local dev service definitions
- `.woodpecker/build.yml`: CI/CD pipeline

**Core Logic:**
- `backend/app/auth/dependencies.py`: Auth dependency chain — touch before adding any new protected endpoint
- `backend/app/database.py`: DB engine, `get_db`, `get_db_context`, `Base`
- `backend/app/modules/base.py`: `BaseModule` ABC — extend for new tenant modules
- `backend/app/modules/registry.py`: Module registry — register new modules here
- `backend/app/services/printer_adapter.py`: `PrinterAdapter` Protocol — implement for new printer types

**Infrastructure:**
- `infrastructure/argocd/application.yaml`: ArgoCD application definition (auto-sync target)
- `infrastructure/k8s/backend/deployment.yaml`: Backend Kubernetes deployment
- `infrastructure/k8s/postgres/statefulset.yaml`: PostgreSQL StatefulSet

**Testing:**
- `backend/tests/api/`: API-level tests (use `client` fixture)
- `backend/tests/unit/`: Unit tests for services and utilities
- `backend/tests/utils/`: Shared fixtures (`client`, `db_session`, `test_tenant`, `test_user`, `test_spool`)

## Where to Add New Code

**New API endpoint (existing resource):**
- Add handler function to existing `backend/app/api/v1/{resource}.py`
- Add corresponding Pydantic schema to `backend/app/schemas/{resource}.py` if new request/response shape
- Add tests in `backend/tests/api/test_{resource}.py`

**New resource (backend):**
1. Model: `backend/app/models/{resource}.py` — inherit `Base, UUIDMixin, TimestampMixin`; add `tenant_id` FK
2. Schema: `backend/app/schemas/{resource}.py` — `{Resource}Create`, `{Resource}Update`, `{Resource}Response`
3. Service (if needed): `backend/app/services/{resource}_service.py` — class with `(db, tenant, user)` constructor
4. Route handler: `backend/app/api/v1/{resource}.py` — `router = APIRouter()`, use `CurrentTenant`, `CurrentUser`
5. Register router: add import and `app.include_router(...)` call in `backend/app/main.py`
6. Migration: `cd backend && poetry run alembic revision --autogenerate -m "add {resource}"`

**New frontend page:**
- Page component: `frontend/src/pages/{ResourceName}.tsx` or `frontend/src/pages/{ResourceName}Page.tsx`
- Route: Add `new Route({...})` in `frontend/src/App.tsx`; wrap with `ProtectedRoute` + `ModuleGuard` if needed
- API client: Add methods to existing `frontend/src/lib/api/{resource}.ts` or create new file

**New feature module (backend):**
1. Create `backend/app/modules/{module_name}/` directory with `__init__.py`
2. Create module class inheriting `BaseModule` (see `backend/app/modules/base.py:37`)
3. Set `name`, `display_name`, `tenant_types`, implement `register_routes()`
4. Register in `backend/app/modules/registry.py`

**New component:**
- Feature component: `frontend/src/components/{feature}/{ComponentName}.tsx`
- UI primitive: `frontend/src/components/ui/{component-name}.tsx` (shadcn/ui pattern)

**Shared hook:**
- `frontend/src/hooks/use{HookName}.ts`

**Utility functions:**
- Backend: `backend/app/utils/{utility}.py`
- Frontend: `frontend/src/utils/{utility}.ts`

## Special Directories

**`backend/alembic/versions/`:**
- Purpose: Database migration files
- Generated: Yes (autogenerate via Alembic)
- Committed: Yes — never hand-edit these; create new revisions only

**`infrastructure/k8s/`:**
- Purpose: Kubernetes manifests applied by ArgoCD
- Generated: No (hand-authored)
- Committed: Yes — changes here trigger ArgoCD sync within ~3 minutes

**`frontend/src/lib/db/`:**
- Purpose: IndexedDB wrapper for offline spool weight updates (`indexeddb.ts`)
- Generated: No
- Committed: Yes

**`backend/.ruff_cache/`, `backend/.pytest_cache/`:**
- Purpose: Tool caches
- Generated: Yes
- Committed: No (gitignored)

**`.woodpecker/`:**
- Purpose: CI pipeline definitions (Woodpecker CI)
- Key pipelines: `build.yml` (Docker build + k3s registry push), `test-fast.yml`, `test-integration.yml`
- Committed: Yes — changes here affect CI immediately on next push

**`.beads/`:**
- Purpose: Beads task tracking system (embedded Dolt database)
- Generated: Yes (managed by Beads CLI)
- Committed: Yes

---

*Structure analysis: 2026-05-19*
