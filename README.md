<p align="center">
  <img src="frontend/public/logo.svg" alt="Batchivo Logo" width="400">
</p>

<h1 align="center">Batchivo</h1>

<p align="center">
  <strong>Self-hosted 3D printing business management platform</strong>
</p>

<p align="center">
  <a href="https://github.com/techize/batchivo/actions/workflows/ci.yml"><img src="https://github.com/techize/batchivo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/techize/batchivo"><img src="https://codecov.io/gh/techize/batchivo/graph/badge.svg" alt="codecov"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.124+-green.svg" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19+-blue.svg" alt="React"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.9+-blue.svg" alt="TypeScript"></a>
</p>

---

## What Is Batchivo?

Batchivo is a self-hosted SaaS platform for running a small 3D printing business: filament inventory, products and BOMs, production runs, orders, pricing, shipping, analytics, and marketplace/shop workflows.

It started as a spreadsheet for tracking real 3D printing work and has grown into a multi-tenant FastAPI/React application intended for private use first, then a public open-source MVP.

---

## Current Status

**Version:** 0.2.0-alpha
**Stage:** Pre-MVP hardening
**Issue tracker:** Beads (`bd`)
**Last status refresh:** 2026-05-01

The project is close to a usable MVP for the core 3D printing workflow. The main product surfaces are implemented, but the backlog still needs E2E coverage, production deployment validation, issue triage after the Task Master migration, and several expansion features.

### Implemented Core

- Multi-tenant authentication, onboarding, tenant membership, settings, modules, and audit surfaces
- Spool, consumable, material, QR/label, scan, and inventory transaction workflows
- Product catalog with BOMs, costing, images, categories, variants, designers, SKU and export support
- Production run API and UI, including plates, completion, variance analysis, reprints, and inventory adjustments
- Orders, customers, sales channels, discounts, returns, shipping rates, newsletter, public shop, and customer account surfaces
- Dashboard, analytics, forecasting, reporting/export, and admin configuration APIs
- Printer fleet foundations: printers, Bambu integration surface, print queue, WebSocket status, and generic webhooks
- Shopify sync/webhook groundwork and Square/payment settings surfaces
- Local Docker Compose, k3s/Cloudflare self-hosting assets, observability configuration, and CI

### MVP Gaps

- E2E coverage for full order/payment/fulfillment workflows is still open in Beads.
- Production deployment needs a fresh end-to-end validation, including wildcard DNS/domain configuration.
- Beads contains imported Task Master issues that need triage because some imported descriptions are stale relative to the code.
- Knitting/multi-craft modules are not MVP-ready: module definitions exist, but yarn/needle routers are placeholders and pattern/project API routers are not implemented.
- Structured production logging, alert rules, complete COGS, marketplace OAuth integrations, and advanced printer automation remain post-MVP or hardening work.

Use [docs/PROJECT-STATUS.md](docs/PROJECT-STATUS.md) for the current status snapshot and [ROADMAP.md](ROADMAP.md) for phase-level priorities.

---

## Tech Stack

**Backend**
- Python 3.12+ with FastAPI
- PostgreSQL with multi-tenant isolation and SQLAlchemy 2.0
- Alembic migrations
- Redis and Celery-ready background job infrastructure
- OpenTelemetry, Prometheus, Grafana, Tempo, and Loki configuration

**Frontend**
- React 19, TypeScript 5.9, Vite 7
- TanStack Query
- Tailwind CSS and local component primitives
- PWA support and responsive admin workflows

**Infrastructure**
- Docker Compose for local development
- k3s/Kubernetes manifests
- Cloudflare Tunnel ingress
- Self-hosting documentation and observability assets

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 20+
- Poetry
- pnpm or npm

### Local Development

```bash
git clone https://github.com/techize/batchivo.git
cd batchivo

docker-compose up -d

cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000

cd ../frontend
pnpm install
pnpm run dev
```

**Access**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Grafana: http://localhost:3000

---

## Issue Tracking

This repository uses Beads.

```bash
bd ready
bd show <id>
bd update <id> --status in_progress
bd close <id> --reason "Completed"
bd export --output .beads/issues.jsonl
```

The old Task Master backlog was migrated into Beads on 2026-05-01. Beads is now the source of truth.

---

## Documentation

- [Project Status](docs/PROJECT-STATUS.md)
- [Roadmap](ROADMAP.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Testing Guide](docs/TESTING.md)
- [Self-Hosting Guide](docs/SELF-HOSTING.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Production Runs](docs/PRODUCTION_RUNS.md)
- [API Reference](docs/api-reference/overview.md)
- [User Guide](docs/user-guide/README.md)
- [Implementation Phases](docs/IMPLEMENTATION_PHASES.md)

---

## Testing

```bash
make test

cd backend && poetry run pytest
cd frontend && pnpm test
```

Last verified snapshot from the Beads repair session on 2026-05-01:

- Backend: 3634 passed, 19 skipped
- Frontend unit tests: 334 passed
- Frontend production audit: 0 vulnerabilities
- Landing build: passed

---

## Development Commands

```bash
make dev          # Start full local development stack
make test         # Run tests
make lint         # Run linters
make format       # Format code
make migrate      # Run database migrations
make build        # Build Docker images
make deploy-dev   # Deploy to k3s dev environment
```

See [Makefile](Makefile) for all available commands.

---

## Deployment

Batchivo is designed for self-hosting on:

- k3s or another lightweight Kubernetes environment
- PostgreSQL
- Redis
- Cloudflare Tunnel
- Prometheus, Grafana, Tempo, and Loki

See [docs/SELF-HOSTING.md](docs/SELF-HOSTING.md) for the current deployment guide.

---

## Security

- Custom JWT authentication with secure refresh tokens
- Multi-tenant data isolation
- Pydantic request validation
- SQLAlchemy ORM query construction
- Environment-based secrets
- TLS via Cloudflare in the intended deployment

Report vulnerabilities privately to the repository owner.

---

## License

This project is expected to be released under MIT or Apache 2.0 once the MVP is stable.

**Current status:** private repository during initial MVP development.

---

## Vision

**Short term:** robust personal 3D printing business management
**Medium term:** public open-source MVP and community feedback
**Long term:** practical operations platform for small 3D printing businesses

*Last updated: 2026-05-01*
