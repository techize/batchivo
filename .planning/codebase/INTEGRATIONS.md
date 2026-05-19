# External Integrations

**Analysis Date:** 2026-05-19

## APIs & External Services

**Payments:**
- Square — Processes shop checkout payments
  - SDK/Client: `squareup` >=42.0.0
  - Service: `backend/app/services/square_payment.py`, `backend/app/services/square_webhook_service.py`
  - Routes: `backend/app/api/v1/payments.py`
  - Auth env vars: `SQUARE_APP_ID`, `SQUARE_ACCESS_TOKEN`, `SQUARE_LOCATION_ID`, `SQUARE_WEBHOOK_SIGNATURE_KEY`
  - Environment toggle: `SQUARE_ENVIRONMENT` (`sandbox` | `production`) — currently sandbox

**Marketplaces:**
- Etsy — Syncs product listings to Etsy marketplace
  - SDK/Client: `etsyv3` >=0.0.7
  - Service: `backend/app/services/etsy_sync.py`
  - Auth: stored encrypted per-tenant in database (fetched via `safe_decrypt`)
  - OAuth tokens stored via `backend/app/core/encryption.py`

- Shopify — Receives order webhooks from Shopify stores; syncs fulfilment back
  - Service: `backend/app/services/shopify_sync.py`
  - Routes: `backend/app/api/v1/shopify_webhooks.py`
  - Auth env vars: `SHOPIFY_WEBHOOK_SECRET` (HMAC validation), `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ACCESS_TOKEN`

**3D Printer Connectivity:**
- Bambu Lab printers — Real-time status, AMS filament, print progress via MQTT over SSL
  - Protocol: MQTT (paho-mqtt >=2.1.0)
  - Service: `backend/app/services/bambu_mqtt.py`
  - Config: per-printer credentials, connects to printer's local MQTT broker on port 8883
  - Schemas: `backend/app/schemas/ams_slot_mapping.py`, `backend/app/schemas/printer_connection.py`

- Klipper/Moonraker printers — Print status and control via HTTP REST
  - Protocol: HTTP (httpx)
  - Adapter: `backend/app/services/moonraker_adapter.py`
  - Config: per-printer `MoonrakerConnectionConfig` (hostname, port)

**Filament Database:**
- SpoolmanDB — Open-source filament material reference data, synced periodically
  - Source: `https://donkie.github.io/SpoolmanDB/filaments.json` and `materials.json`
  - Service: `backend/app/services/spoolmandb_sync.py`
  - No auth required (public CDN)

**Email:**
- Brevo (formerly Sendinblue) — Transactional email (order confirmations, verification emails)
  - API: `https://api.brevo.com/v3/smtp/email` (HTTPS REST)
  - Service: `backend/app/services/email_service.py`
  - Auth env var: `BREVO_API_KEY`
  - From address: configured via `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME`
  - Note: `backend/app/config.py` references `resend` in a comment (line 964) but Brevo is the active implementation

## Data Storage

**Primary Database:**
- PostgreSQL 16 (Alpine) — All application data
  - k8s: `infrastructure/k8s/postgres/statefulset.yaml`
  - Connection env var: `DATABASE_URL` (default: `postgresql+psycopg://batchivo:batchivo@localhost:5432/batchivo`)
  - Client: SQLAlchemy 2.0 async with psycopg3 driver
  - RLS: Row-Level Security enabled per-tenant via `app_user` role (`RLS_ENABLED`, `RLS_DATABASE_URL`)
  - Migrations: Alembic (`backend/alembic/versions/`)

**File Storage:**
- MinIO (self-hosted S3-compatible) — Production image/file storage
  - k8s: `infrastructure/k8s/minio/minio.yaml`
  - Client: boto3 >=1.35.0 via `backend/app/services/image_storage.py`
  - Auth env vars: `STORAGE_S3_ACCESS_KEY`, `STORAGE_S3_SECRET_KEY`, `STORAGE_S3_ENDPOINT`
  - Bucket: configured via `STORAGE_S3_BUCKET` (default: `batchivo-images`)
  - Toggle: `STORAGE_TYPE` = `local` (dev) | `s3` (production)

- Local filesystem — Development file storage
  - Path: `STORAGE_PATH` (default: `./uploads`)

**Caching:**
- Redis 7 (Alpine) — Application cache + Celery broker
  - k8s: `infrastructure/k8s/redis/deployment.yaml`
  - Connection env var: `REDIS_URL` (default: `redis://localhost:6379/0`)
  - Cache service: `backend/app/services/cache_service.py`
  - Celery broker: `CELERY_BROKER_URL` (`redis://localhost:6379/1`)
  - Celery results: `CELERY_RESULT_BACKEND` (`redis://localhost:6379/2`)
  - TTL: `CACHE_DEFAULT_TTL` (default: 300s / 5 min)

## Authentication & Identity

**Auth Provider:**
- Custom JWT (no third-party auth provider)
  - Implementation: `backend/app/core/security.py`
  - Access token: `PyJWT` HS256, expires in 24h (`ACCESS_TOKEN_EXPIRE_MINUTES`)
  - Refresh tokens: supported
  - Password hashing: bcrypt (`backend/app/auth/password.py`)
  - Dependency injection: `backend/app/auth/dependencies.py` (admin), `backend/app/auth/customer_dependencies.py` (shop customers)
  - Token signing key: `SECRET_KEY` environment variable (required, >=32 chars)
  - Multi-tenant: every authenticated request scoped to `tenant_id` via `get_current_tenant()` dependency

**Encryption:**
- `backend/app/core/encryption.py` — Field-level encryption for sensitive per-tenant data (e.g., Etsy OAuth tokens)

## Monitoring & Observability

**Error Tracking:**
- Sentry — Both backend and frontend
  - Backend DSN: `SENTRY_DSN` env var; initialised in `backend/app/observability/sentry.py`
  - Frontend DSN: `VITE_SENTRY_DSN`; initialised in `frontend/src/lib/sentry.ts`
  - Source maps: uploaded during Vite build via `@sentry/vite-plugin` when `SENTRY_AUTH_TOKEN` present
  - Sample rate: `SENTRY_TRACES_SAMPLE_RATE` (default: 0.1)

**Distributed Tracing:**
- Grafana Tempo — OTLP trace collection
  - Config: `infrastructure/observability/tempo.yaml`
  - Backend exporter: `opentelemetry-exporter-otlp` → `OTEL_EXPORTER_OTLP_ENDPOINT`
  - Frontend exporter: `@opentelemetry/exporter-trace-otlp-http` via `frontend/src/lib/telemetry.ts`
  - Service name: `OTEL_SERVICE_NAME` / `VITE_SERVICE_NAME`

**Metrics:**
- Prometheus — Scrapes backend metrics endpoint (`/metrics`)
  - Config: `infrastructure/observability/prometheus.yml`
  - Backend: `opentelemetry-exporter-prometheus` >=0.48b0
  - k8s service discovery in `batchivo` namespace

**Dashboards:**
- Grafana — Deployed in observability stack (`infrastructure/observability/grafana/`)

**Web Analytics:**
- Umami — Self-hosted privacy-first analytics
  - k8s: `infrastructure/k8s/umami/deployment.yaml`
  - Endpoint: `https://analytics.batchivo.com` (injected in `landing/app/layout.tsx`)

## CI/CD & Deployment

**Hosting:**
- k3s — Self-managed Kubernetes cluster
- Cloudflare Tunnel — Ingress without exposed ports (`infrastructure/cloudflare/`)
- cert-manager — TLS certificates (`infrastructure/k8s/cert-manager/`)
- Self-hosted container registry: `registry.techize.co.uk`

**CI Pipeline:**
- Woodpecker CI (`https://ci.techize.co.uk`)
  - Pipeline files: `.woodpecker/build.yml`, `.woodpecker/test-fast.yml`, `.woodpecker/test-integration.yml`, `.woodpecker/ci-image.yml`
  - Build: Kaniko/buildctl via BuildKit daemon — no Docker socket required
  - Layer cache stored in registry for warm builds
  - On push to `main`: build backend + frontend images in parallel → deploy-staging → deploy-production

**CD:**
- ArgoCD (`https://argocd.techize.co.uk`) — Watches `infrastructure/k8s/` manifests
  - Auto-syncs within ~3 minutes of manifest change
  - Staging: `infrastructure/k8s/staging/deployment.yaml`
  - Production: `infrastructure/k8s/backend/deployment.yaml`, `infrastructure/k8s/frontend/`

## Webhooks & Callbacks

**Incoming Webhooks:**
- Square payments: `POST /api/v1/payments/webhooks/square`
  - Verified via `SQUARE_WEBHOOK_SIGNATURE_KEY` HMAC
  - Events: `payment.created`, `payment.updated`, `refund.created`, `refund.updated`
  - Handler: `backend/app/services/square_webhook_service.py`

- Shopify orders: `POST /api/v1/shopify/webhooks/{event}`
  - Verified via `SHOPIFY_WEBHOOK_SECRET` HMAC
  - Handler: `backend/app/api/v1/shopify_webhooks.py`, `backend/app/services/shopify_sync.py`

- Generic outbound webhooks: `POST /api/v1/webhooks/{tenant_slug}`
  - Per-tenant webhook delivery for external integrations
  - Handler: `backend/app/api/v1/webhooks.py`, `backend/app/services/webhook_service.py`

**Outgoing (not webhooks):**
- Bambu MQTT: persistent outbound connections to individual printers (TCP 8883)
- Moonraker: outbound HTTP polls to local Klipper printers
- Etsy API: outbound REST calls to `openapi.etsy.com`
- SpoolmanDB: outbound GET to `donkie.github.io`

## Environment Configuration

**Required env vars (backend):**
- `SECRET_KEY` — JWT signing key (no default; hard fail on startup if missing)
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string

**Optional but production-critical env vars:**
- `SQUARE_ACCESS_TOKEN`, `SQUARE_APP_ID`, `SQUARE_LOCATION_ID`, `SQUARE_WEBHOOK_SIGNATURE_KEY`
- `SHOPIFY_WEBHOOK_SECRET`, `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ACCESS_TOKEN`
- `BREVO_API_KEY`, `EMAIL_FROM_ADDRESS`
- `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`
- `STORAGE_TYPE`, `STORAGE_S3_ACCESS_KEY`, `STORAGE_S3_SECRET_KEY`, `STORAGE_S3_ENDPOINT`, `STORAGE_S3_BUCKET`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `RLS_ENABLED`, `RLS_DATABASE_URL`

**Secrets location (production):**
- Kubernetes Secrets in `batchivo` namespace
- Templates: `infrastructure/k8s/backend/secrets.yaml.template`
- Square: `kubectl get secret square-credentials -n batchivo`
- Resend/Brevo: `kubectl get secret resend-credentials -n batchivo`
- Registry auth: Woodpecker CI secrets (`docker_username`, `docker_password`, `github_token`)

---

*Integration audit: 2026-05-19*
