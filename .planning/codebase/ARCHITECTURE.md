<!-- refreshed: 2026-05-19 -->
# Architecture

**Analysis Date:** 2026-05-19

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React SPA)                         │
│  `frontend/src/App.tsx`  |  TanStack Router + TanStack Query         │
│  Pages, Components, Hooks, Guards, API clients                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTPS/REST + WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                               │
│  `backend/app/main.py`                                               │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  Middleware  │  │  Auth Layer │  │  API Routes (v1)          │   │
│  │  CORS, RLS   │  │  JWT, Tenant│  │  `backend/app/api/v1/`   │   │
│  │  Security    │  │  Context    │  │  ~45 route modules        │   │
│  └──────────────┘  └─────────────┘  └──────────────────────────┘   │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │   Services   │  │   Schemas   │  │   Feature Modules         │   │
│  │  (business   │  │  (Pydantic) │  │ `backend/app/modules/`   │   │
│  │   logic)     │  │             │  │  threed_print, knitting   │   │
│  └──────────────┘  └─────────────┘  └──────────────────────────┘   │
│  ┌──────────────┐  ┌─────────────────────────────────────────────┐  │
│  │    Models    │  │            Observability                     │  │
│  │ (SQLAlchemy) │  │  Sentry, OpenTelemetry (traces + metrics)   │  │
│  └──────────────┘  └─────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┼──────────────────────┐
          ▼                ▼                       ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  PostgreSQL   │  │  Redis           │  │  MinIO (S3-compat.)  │
│  (+ RLS)      │  │  Cache + Celery  │  │  Product images      │
│  90 migrations│  │  broker          │  │  `image_storage.py`  │
└──────────────┘  └──────────────────┘  └──────────────────────┘
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

**Overall:** Multi-tenant SaaS with pluggable feature modules, PostgreSQL Row-Level Security for data isolation, and custom JWT authentication.

**Key Characteristics:**
- Every database table carries `tenant_id`; RLS policies enforce isolation at the PostgreSQL layer
- Feature modules (3D printing, knitting) are enabled/disabled per-tenant type; module system uses `BaseModule` abstract class in `backend/app/modules/base.py`
- API routes are thin — business logic lives in dedicated service classes under `backend/app/services/`
- Frontend uses TanStack Query for server state; `ModuleGuard` components protect module-gated routes
- Two separate auth flows: internal users (JWT) and storefront customers (`customer_auth` / `customer_dependencies`)

## Layers

**Middleware Layer:**
- Purpose: Cross-cutting concerns applied before route handlers
- Location: `backend/app/middleware/`, `backend/app/auth/middleware.py`
- Contains: `TenantContextMiddleware` (extracts tenant_id from JWT → `request.state.tenant_id`), `SecurityHeadersMiddleware`, `MetricsMiddleware`, `CORSPreflightMiddleware`
- Depends on: `backend/app/core/security.py` (JWT decode)
- Used by: All requests

**Auth / Dependency Layer:**
- Purpose: FastAPI dependencies that validate tokens, resolve tenants, set RLS context
- Location: `backend/app/auth/dependencies.py`
- Contains: `get_current_user`, `get_current_tenant`, `get_tenant_db` (sets `SET LOCAL app.current_tenant_id`), `get_shop_tenant`, `get_platform_admin`, role hierarchy checking
- Depends on: Models, core/security
- Used by: All protected route handlers

**API Layer:**
- Purpose: Route handlers — validate input, call services or direct DB queries, return schemas
- Location: `backend/app/api/v1/`
- Contains: ~45 router modules (spools, models, products, orders, payments, printers, shop, platform, etc.)
- Depends on: Auth dependencies, services, models, schemas
- Used by: FastAPI router registration in `main.py`

**Service Layer:**
- Purpose: Encapsulates business logic that is too complex for route handlers
- Location: `backend/app/services/`
- Contains: `ProductionRunService`, `PrintQueueService`, `EmailService`, `SquarePaymentService`, `ShopifySyncService`, `EtsySyncService`, `ImageStorageService`, `InventoryTransactionService`, `ForecastingService`, etc.
- Pattern: Service classes instantiated with `(db, tenant, user)` constructor; stateless helpers as module-level functions
- Depends on: Models, schemas, external clients
- Used by: API route handlers

**Module Layer:**
- Purpose: Pluggable feature groupings enabled per tenant type
- Location: `backend/app/modules/`
- Contains: `BaseModule` ABC (`modules/base.py`), module registry (`modules/registry.py`), `threed_print/` (categories, consumables, designers, models, orders, printers, production, products, sales_channels, spools), `knitting/` (needle, pattern, project, yarn)
- Depends on: API routes it wraps
- Used by: `backend/app/api/v1/modules.py` (module info endpoint), tenant module access control

**Data Layer:**
- Purpose: Database models and schema definitions
- Location: `backend/app/models/`, `backend/app/schemas/`
- Contains: 40+ SQLAlchemy models using `UUIDMixin` + `TimestampMixin` from `models/base.py`, corresponding Pydantic schemas
- Pattern: Models inherit `Base, UUIDMixin, TimestampMixin`; all tenant-scoped models have `tenant_id` column
- Depends on: `backend/app/database.py` for `Base`
- Used by: Services, route handlers

**Frontend Layer:**
- Purpose: React SPA for the management console
- Location: `frontend/src/`
- Contains: Pages, feature components, API clients, auth context, hooks, guards
- Pattern: TanStack Query for server state caching; typed API clients per resource in `lib/api/*.ts`; `ModuleGuard` wraps module-gated routes; `PlatformAdminGuard` protects platform admin pages

## Data Flow

### Authenticated API Request

1. Browser sends `Authorization: Bearer <jwt>` + `X-Tenant-ID: <uuid>` → `backend/app/main.py`
2. `TenantContextMiddleware.dispatch()` decodes JWT, stores `tenant_id` in `request.state` (`backend/app/auth/middleware.py:66`)
3. Route handler declares `tenant: CurrentTenant = Depends(get_current_tenant)` → `backend/app/auth/dependencies.py:73`
4. `get_current_tenant` validates user has access to requested tenant
5. If using `TenantDB` dependency, `get_tenant_db` executes `SET LOCAL app.current_tenant_id = :tenant_id` on the session (`backend/app/auth/dependencies.py:278`)
6. Route handler calls service or executes SQLAlchemy query (filtered by RLS automatically)
7. Response serialised via Pydantic schema, returned as JSON

### Public Storefront Request

1. Shop frontend sends request with `X-Shop-Hostname: mystmereforge.co.uk`
2. `get_shop_tenant` dependency resolves tenant by custom domain or subdomain extraction (`backend/app/auth/dependencies.py:336`)
3. Route handler uses `ShopTenant` / `ShopContext` — no user auth required
4. Queries run without RLS tenant context (shop endpoints filter by tenant_id explicitly)

### WebSocket (Printer Monitoring)

1. Client connects to `ws://host/ws/printers` (`backend/app/api/v1/printer_ws.py`)
2. WebSocket mounted at root without `/api/v1` prefix (`main.py:257`)
3. `PrinterRegistry` (`backend/app/services/printer_registry.py`) manages live printer state
4. Bambu MQTT adapter (`backend/app/services/bambu_mqtt.py`) and Moonraker adapter (`backend/app/services/moonraker_adapter.py`) implement `PrinterAdapter` protocol (`backend/app/services/printer_adapter.py`)

### Token Refresh Flow

1. Axios interceptor in `frontend/src/lib/api.ts` detects expired access token
2. Posts `refresh_token` to `/api/v1/auth/refresh`
3. Queues concurrent requests during refresh; replays them with new access token

**State Management (Frontend):**
- Server state: TanStack Query (`@tanstack/react-query`) with 1 retry, no window-focus refetch
- Auth state: `AuthContext` in `frontend/src/contexts/AuthContext.tsx`
- Offline spools: IndexedDB via `frontend/src/lib/db/indexeddb.ts` + `frontend/src/hooks/useOfflineSpools.ts`

## Key Abstractions

**BaseModule:**
- Purpose: Abstract base for all pluggable feature modules
- File: `backend/app/modules/base.py`
- Pattern: Subclasses set `name`, `display_name`, `tenant_types`, `is_core`; implement `register_routes(router)`. `is_enabled_for_tenant(tenant)` checks `tenant.tenant_type` against `tenant_types` list.

**PrinterAdapter Protocol:**
- Purpose: Uniform interface for multiple printer hardware types
- File: `backend/app/services/printer_adapter.py`
- Pattern: Python `Protocol` (structural subtyping) — Bambu (`bambu_mqtt.py`) and Moonraker (`moonraker_adapter.py`) both satisfy without explicit inheritance

**CurrentTenant / CurrentUser / TenantDB Type Aliases:**
- Purpose: Clean dependency injection into route handlers
- File: `backend/app/auth/dependencies.py` (lines 219–296)
- Pattern: `CurrentUser = Annotated[User, Depends(get_current_user)]` — used as parameter type hints in route functions

**apiClient (Frontend):**
- Purpose: Typed resource-specific API clients using shared axios instance
- File: `frontend/src/lib/api.ts` (base client), `frontend/src/lib/api/*.ts` (resource clients)
- Pattern: Each resource file exports an object (`spoolsApi`, `modelsApi`, etc.) with typed async methods that call `apiClient.get/post/put/delete`

## Entry Points

**Backend:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app` or Kubernetes deployment
- Responsibilities: Creates FastAPI app, registers middleware (order matters), mounts all API routers, serves static images

**Frontend:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser load / Vite dev server / Docker+nginx
- Responsibilities: Initialises Sentry, optional OpenTelemetry, wraps app in `ErrorBoundary`, renders `App`

**Frontend Routing:**
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

**What happens:** Several route handlers (e.g., `backend/app/api/v1/spools.py`) execute `select()` queries directly in the route function rather than delegating to a service.
**Why it's wrong:** Business logic duplicates across routes; harder to test; violates the pattern established by `ProductionRunService`, `PrintQueueService`, etc.
**Do this instead:** Extract to a service class in `backend/app/services/` that accepts `(db, tenant, user)` and encapsulates all queries.

### `get_db` Used Instead of `get_tenant_db` for Tenant-Scoped Data

**What happens:** Some routes import `get_db` directly rather than using the `TenantDB` type alias.
**Why it's wrong:** Bypasses the `SET LOCAL app.current_tenant_id` RLS context setup, meaning RLS policies are not enforced for that session.
**Do this instead:** Use `db: TenantDB` (from `backend/app/auth/dependencies.py`) for any endpoint that reads/writes tenant-scoped data.

## Error Handling

**Strategy:** FastAPI `HTTPException` for user-facing errors; unhandled exceptions propagate to Sentry. Service layer raises `HTTPException` directly (no custom exception hierarchy).

**Patterns:**
- Auth failures → `HTTP 401` with `WWW-Authenticate: Bearer` header
- Permission failures → `HTTP 403`
- Not found → `HTTP 404`
- Validation failures → `HTTP 422` (automatic from Pydantic)
- Database errors → rolled back automatically in `get_db` / `get_tenant_db` session context managers

## Cross-Cutting Concerns

**Logging:** Standard Python `logging` module. Each module creates `logger = logging.getLogger(__name__)`. No centralised structured logging format enforced.
**Validation:** Pydantic schemas on all request/response bodies. Input validated at route boundary. Additional FK validation helpers (e.g., `ensure_material_type_exists`) in some route files.
**Authentication:** Custom JWT (`HS256`) via `backend/app/core/security.py`. No OAuth provider. Separate customer auth flow via `backend/app/auth/customer_dependencies.py`.
**Caching:** Redis via `backend/app/services/cache_service.py`. Cache toggleable per-env via `settings.cache_enabled`.
**Audit logging:** `backend/app/services/audit_service.py` + `backend/app/models/audit_log.py` for recording significant mutations.

---

*Architecture analysis: 2026-05-19*
