# Technology Stack

**Analysis Date:** 2026-05-19

## Languages

**Primary:**
- Python 3.12 - Backend API (`backend/`)
- TypeScript 5.9 - Frontend SPA (`frontend/`) and docs site (`docs-site/`)

**Secondary:**
- TypeScript 5.x - Landing page (`landing/`)
- YAML - Infrastructure as code (`infrastructure/`)

## Runtime

**Backend:**
- CPython 3.12 (Alpine Linux in Docker)
- Constraint: `requires-python = ">=3.12,<4.0"` in `backend/pyproject.toml`

**Frontend:**
- Node.js (version not pinned via `.nvmrc` — check `frontend/Dockerfile` for exact version)

## Package Managers

**Backend:**
- Poetry >=2.0.0 (PEP 621 with `pyproject.toml`)
- Lockfile: `backend/poetry.lock` (present)
- Alt npm lockfile present at `backend/package-lock.json` (legacy artifact)

**Frontend:**
- pnpm (primary — `frontend/pnpm-lock.yaml` present)
- npm lockfile also present (`frontend/package-lock.json`) — pnpm is canonical
- Landing page: npm (`landing/package-lock.json`)
- Docs site: npm (`docs-site/package-lock.json`)

## Frameworks

**Backend:**
- FastAPI >=0.124.4 — REST API framework (`backend/app/main.py`)
- SQLAlchemy 2.0 (async) — ORM (`backend/app/database.py`, `backend/app/models/`)
- Alembic >=1.13.0 — Database migrations (`backend/alembic/`)
- Pydantic v2 + pydantic-settings — Settings and schema validation (`backend/app/config.py`, `backend/app/schemas/`)
- Starlette 0.49.3 (pinned) — ASGI foundation under FastAPI

**Frontend:**
- React 19.2 — UI framework (`frontend/src/`)
- Vite 7.x — Build tool and dev server (`frontend/vite.config.ts`)
- TanStack Router 1.141 — File-based routing (`frontend/src/routes/`)
- TanStack Query 5.90 — Server state / data fetching (`frontend/src/`)
- shadcn/ui — Component library built on Radix UI (`frontend/src/components/`)
- Tailwind CSS 3.4 — Utility-first styling
- Zod 4.x — Schema validation on frontend
- react-hook-form 7.x — Form management

**Landing:**
- Next.js 16.2 — Static/SSR marketing site (`landing/`)
- Tailwind CSS 4 — Styling

**Docs:**
- Docusaurus 3.9.2 — Documentation site (`docs-site/`)

**Background Jobs:**
- Celery >=5.3.0 with Redis broker — Async task queue (configured in `backend/app/config.py`, broker: `redis://localhost:6379/1`)

**API Server:**
- Uvicorn[standard] >=0.38.0 — ASGI server

## Key Dependencies

**Critical:**
- `psycopg[binary,pool]` >=3.1.0 — PostgreSQL async driver (`backend/`)
- `asyncpg` >=0.31.0 — Additional async PostgreSQL driver
- `redis` >=5.0.0 — Redis client for caching and Celery
- `PyJWT` >=2.12.0 — Custom JWT authentication (`backend/app/core/security.py`)
- `bcrypt` >=4.0.0 — Password hashing (`backend/app/auth/password.py`)
- `authlib` >=1.6.9 — OAuth2 client support
- `httpx` >=0.26.0 — Async HTTP client for external service calls
- `slowapi` >=0.1.9 — Rate limiting middleware (`backend/app/core/rate_limit.py`)

**Domain-Specific:**
- `squareup` >=42.0.0 — Square Payments SDK (`backend/app/services/square_payment.py`)
- `etsyv3` >=0.0.7 — Etsy API SDK (`backend/app/services/etsy_sync.py`)
- `boto3` >=1.35.0 — AWS/MinIO S3 SDK (`backend/app/services/image_storage.py`)
- `paho-mqtt` >=2.1.0 — MQTT for Bambu Lab printer communication (`backend/app/services/bambu_mqtt.py`)
- `qrcode[pil]` >=7.4.0 — QR code generation (`backend/app/`)
- `pillow` >=12.2.0 — Image processing

**Observability:**
- `opentelemetry-api/sdk` >=1.27.0 — Backend tracing and metrics
- `opentelemetry-exporter-otlp` >=1.27.0 — Exports to Tempo (OTLP)
- `opentelemetry-exporter-prometheus` >=0.48b0 — Prometheus metrics endpoint
- `sentry-sdk[fastapi]` >=2.0.0 — Error tracking (`backend/app/observability/sentry.py`)
- `@sentry/react` >=8.0.0 — Frontend error tracking (`frontend/src/lib/sentry.ts`)
- `@opentelemetry/*` — Frontend distributed tracing (`frontend/src/lib/telemetry.ts`)

**Testing (backend):**
- `pytest` >=9.0.3 + `pytest-asyncio` >=1.3.0 + `pytest-cov` >=4.1.0
- `fakeredis` >=2.32.1 — Redis mocking
- `moto[s3]` >=5.0.0 — AWS S3 mocking
- `respx` >=0.21.0 — httpx request mocking
- `pytest-xdist` >=3.8.0 — Parallel test execution

**Testing (frontend):**
- Vitest 4.x — Unit/component test runner
- Playwright 1.59 — E2E tests (`frontend/src/test/`)
- `@testing-library/react` 16.x + `@testing-library/user-event`
- Storybook 10.x — Component development and visual testing

## Configuration

**Backend Environment:**
- Config: `backend/app/config.py` — `pydantic-settings` reads from `.env` + environment variables
- Required: `SECRET_KEY` (no default — enforced by validator)
- Key groups: database, Redis, CORS, OpenTelemetry, Celery, storage (local/S3), Square, Shopify, Brevo email, Sentry

**Frontend Runtime Config:**
- `frontend/src/lib/config.ts` — reads from `window.__RUNTIME_CONFIG__` (set at container startup) with fallback to `import.meta.env`
- Allows runtime injection without rebuilding images
- Key vars: `VITE_API_URL`, `VITE_OTEL_ENDPOINT`, `VITE_SENTRY_DSN`, `VITE_BUILD_SHA`

**Build Config:**
- `frontend/vite.config.ts` — code splitting, proxy rules, Sentry source map upload
- `backend/pyproject.toml` — `[tool.ruff]`, `[tool.black]`, `[tool.mypy]`, `[tool.pytest.ini_options]`
- `frontend/tsconfig.json` — TypeScript strict mode, path alias `@` → `./src`

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js (recent LTS)
- PostgreSQL 16 (or Docker)
- Redis 7 (or Docker)
- Docker Compose: `docker-compose.yml` at repo root

**Production:**
- k3s Kubernetes cluster (`infrastructure/k8s/`)
- Cloudflare Tunnel for ingress (`infrastructure/cloudflare/`)
- Self-hosted container registry: `registry.techize.co.uk`
- CI: Woodpecker CI at `https://ci.techize.co.uk`
- CD: ArgoCD at `https://argocd.techize.co.uk`
- Docker images: Python 3.12-Alpine (backend), Node Alpine (frontend)

---

*Stack analysis: 2026-05-19*
