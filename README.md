# Nozzly

**Complete 3D printing business management platform**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

---

## 🎯 What is Nozzly?

Nozzly is a comprehensive, self-hosted SaaS platform for managing 3D printing businesses. From filament inventory tracking to multi-marketplace pricing strategies, Nozzly helps you run your 3D printing operation professionally and profitably.

**Born from need**: Started as an extensive spreadsheet for tracking personal 3D printing projects, evolved into a full-featured business management system that the community can benefit from.

**Philosophy**: Build for personal use first, open source second, monetization later (maybe).

---

## ✨ Features

### Current Status: 🚧 In Development

**Completed Features** ✅

**Phase 1: Foundation & Authentication**
- [x] Project structure and infrastructure
- [x] Multi-tenant architecture with Row-Level Security
- [x] Custom JWT authentication with secure refresh tokens
- [x] JWT token management with automatic refresh
- [x] Full observability stack (OpenTelemetry, Prometheus, Grafana, Tempo, Loki)
- [x] Backend deployment on k3s cluster
- [x] Frontend deployment with Cloudflare ingress
- [x] Shared AppLayout component with navigation

**Phase 2: Inventory Management** (Partially Complete)
- [x] Spool database models and migrations
- [x] Spool API endpoints (CRUD, filtering, search)
- [x] Spool frontend components (list, detail, create, edit forms)
- [x] Material types and color tracking
- [x] Weight tracking and purchase history

**Phase 3: Product Catalog & Costing** (Partially Complete)
- [x] Product database models (Product, ProductMaterial, ProductComponent)
- [x] Product API endpoints with comprehensive costing
- [x] Product frontend components (list, create, edit)
- [x] Multi-material Bill of Materials (BOM)
- [x] Component cost tracking
- [x] Automatic cost calculation service
- [x] Material usage estimation per product

**Phase 4: Production Run System** (Database Complete, API/UI Pending)
- [x] Production run database models and migrations
- [x] Support for batch printing (multiple products on one bed)
- [x] Multi-color print tracking with purge/waste
- [x] Spool weighing (before/after) and manual weight entry
- [x] Variance analysis (estimated vs actual)
- [x] Reprint tracking and quality rating (1-5 stars)
- [ ] Production run API endpoints
- [ ] Production run frontend UI
- [ ] Inventory integration on run completion

### Planned Features

#### 📦 Inventory Management (Partially Complete)
- ✅ Track filament spools with unique IDs
- ✅ Material types, colors, brands, finishes
- ✅ Purchase history and supplier tracking
- ✅ Weight tracking (initial, current, remaining)
- ⏳ QR code generation and scanning
- ⏳ Low stock alerts and reorder automation

#### 🎨 Product Catalog & Costing (Partially Complete)
- ✅ Product database with SKUs
- ✅ Multi-material Bill of Materials (BOM)
- ✅ Component cost tracking (magnets, inserts, etc.)
- ✅ Labor and overhead allocation
- ✅ Automatic cost calculation
- ⏳ Product images and categorization

#### 🏭 Production Run System (Database Complete)
- ✅ Track actual manufacturing data per print job
- ✅ Batch printing support (multiple products on one bed)
- ✅ Multi-color prints with purge/waste tracking
- ✅ Spool weighing (before/after) or manual weight entry
- ✅ Variance analysis (estimated vs actual filament usage)
- ✅ Quality tracking (1-5 star rating + notes)
- ✅ Reprint workflow (link to original failed run)
- ✅ Run numbering format: {tenant}-YYYYMMDD-NNN
- ⏳ Production run API endpoints
- ⏳ Production run frontend UI (create, complete, detail, list)
- ⏳ Automatic inventory deduction on run completion
- ⏳ Variance alerts and BOM update recommendations

#### 💰 Intelligent Pricing Engine
- Multi-marketplace pricing calculator (Etsy, eBay, Shopify, local fairs)
- Platform-specific fee calculations
- Break-even analysis
- Target margin optimization
- Side-by-side platform comparison
- Export pricing sheets

#### 📊 Sales & Order Tracking
- Order management with status tracking
- Automatic inventory deduction on sale
- Customer database
- Sales analytics and trends
- Profit tracking by product and channel

#### 🔄 Reorder Management
- Usage rate calculations
- Lead time tracking per supplier
- Automatic reorder point calculations
- Purchase order generation
- Supplier performance tracking

#### 📱 Mobile-Friendly PWA
- Desktop-first, mobile-responsive design
- Installable Progressive Web App
- Offline capability
- Camera access for QR code scanning
- Quick update workflows

#### 📈 Analytics & Reporting
- Inventory value dashboard
- Sales trends and forecasting
- Profit analysis by product/channel
- Material usage patterns
- Inventory turnover metrics
- Exportable reports (CSV, PDF)

#### 🔌 Integrations (Future)
- Etsy API (auto-import orders)
- eBay API
- Shopify webhooks
- .gcode file parser (extract material usage)
- OctoPrint integration
- Bambu Connect integration

---

## 🏗️ Architecture

### Tech Stack

**Backend**
- **Python** with **FastAPI** - Modern, fast, async API framework
- **PostgreSQL** - Relational database with row-level security for multi-tenancy
- **SQLAlchemy 2.0** - Async ORM
- **Celery + Redis** - Background job processing
- **OpenTelemetry** - Comprehensive observability

**Frontend**
- **React 18 + TypeScript** - Type-safe UI development
- **shadcn/ui** - Beautiful, accessible component library
- **TanStack Query** - Powerful data fetching
- **Tailwind CSS** - Utility-first styling
- **Vite** - Lightning-fast build tool
- **PWA** - Installable, offline-capable

**Infrastructure**
- **k3s** - Lightweight Kubernetes
- **Cloudflare Tunnel** - Secure ingress
- **Tempo + Prometheus + Grafana + Loki** - Full observability stack

### Why Multi-Tenant?

Built from day one as a proper SaaS platform:
- Multiple businesses can use a single deployment
- Complete data isolation via PostgreSQL Row-Level Security
- Per-tenant customization and branding (future)
- Efficient resource utilization

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Poetry (Python package manager)
- pnpm or npm

### Local Development

```bash
# Clone repository
git clone https://github.com/techize/nozzly.app.git
cd nozzly.app

# Start infrastructure (PostgreSQL, Redis, Observability)
docker-compose up -d

# Backend setup
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
pnpm install
pnpm run dev
```

**Access**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000

### Production Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for k3s deployment instructions.

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive context for AI agents
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and technical details
- **[DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Complete database schema
- **[PRODUCTION_RUNS.md](docs/PRODUCTION_RUNS.md)** - Production Run system design document
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Local development guide
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[IMPLEMENTATION_PHASES.md](docs/IMPLEMENTATION_PHASES.md)** - Development roadmap
- **[API.md](docs/API.md)** - API endpoint documentation

---

## 🎯 Project Status

**Current Phase**: Phase 4 - Production Run System (API & UI implementation)

### Roadmap

**Completed** ✅
- [x] Project initialization
- [x] Architecture design
- [x] Documentation structure
- [x] Backend scaffolding (FastAPI + SQLAlchemy)
- [x] Frontend scaffolding (React + TypeScript + shadcn/ui)
- [x] Authentication system (custom JWT with refresh tokens)
- [x] Database setup (PostgreSQL with RLS)
- [x] Observability configuration (OpenTelemetry, Prometheus, Grafana, Tempo, Loki)
- [x] k3s deployment infrastructure
- [x] Phase 1: Authentication system (complete)
- [x] Phase 2: Core inventory management (Spools - database, API, UI complete)
- [x] Phase 3: Product catalog & costing (database, API, UI complete)
- [x] Phase 4: Production Run system (database models and migrations complete)

**In Progress** 🚧
- [ ] Phase 4: Production Run API endpoints (15 tasks, expanding into subtasks)
- [ ] Phase 4: Production Run frontend UI
- [ ] Phase 4: Inventory integration on run completion

**Upcoming** ⏳
- [ ] Phase 5: Intelligent pricing engine (multi-marketplace calculator)
- [ ] Phase 6: Sales & order tracking
- [ ] Phase 7: Reorder management & alerts
- [ ] Phase 8: QR code scanning (label printing & scanning)
- [ ] Phase 9: Analytics dashboard & reporting
- [ ] Phase 10: Marketplace integrations (Etsy, eBay, Shopify APIs)

See [IMPLEMENTATION_PHASES.md](docs/IMPLEMENTATION_PHASES.md) for detailed timeline and **[PRODUCTION_RUNS.md](docs/PRODUCTION_RUNS.md)** for Production Run system design.

---

## 🤝 Contributing

**Current Status**: Private development for MVP

Once we reach a stable MVP, this project will be open-sourced under MIT or Apache 2.0 license. We welcome:

- Feature suggestions
- Bug reports
- Documentation improvements
- Code contributions
- UI/UX feedback

Stay tuned for CONTRIBUTING.md!

---

## 🔒 Security

### Reporting Vulnerabilities

If you discover a security vulnerability, please email security@nozzly.app (or contact repository owner) directly. Do not create a public issue.

### Security Features

- Custom JWT authentication with secure refresh tokens
- Row-level security for multi-tenant data isolation
- Input validation via Pydantic
- SQL injection protection via SQLAlchemy ORM
- XSS protection via React and CSP headers
- Secrets managed via environment variables
- TLS enforced via Cloudflare

---

## 📊 Observability

Nozzly includes comprehensive observability from day one:

- **Traces**: OpenTelemetry → Tempo → Jaeger UI
- **Metrics**: Prometheus → Grafana
- **Logs**: Loki → Grafana
- **Dashboards**: Pre-configured Grafana dashboards for application, database, and business metrics

Access Grafana at http://localhost:3000 (local dev) or https://grafana.nozzly.app (production).

---

## 🧪 Testing

```bash
# Run all tests
make test

# Backend tests only
cd backend && poetry run pytest

# Frontend tests only
cd frontend && pnpm test

# Test coverage
make test-coverage
```

**Coverage Target**: 80%+

---

## 🛠️ Development Commands

```bash
make dev          # Start full local development stack
make test         # Run all tests
make lint         # Run linters (ruff, mypy, eslint)
make format       # Format code (black, prettier)
make migrate      # Run database migrations
make build        # Build Docker images
make deploy-dev   # Deploy to k3s dev environment
```

See [Makefile](Makefile) for all available commands.

---

## 🌐 Deployment

Nozzly is designed to be self-hosted on your own infrastructure:

- **k3s cluster** (lightweight Kubernetes)
- **Cloudflare Tunnel** for secure ingress (no exposed ports)
- **PostgreSQL** as StatefulSet
- **Redis** for caching and job queue
- **Tempo/Prometheus/Loki/Grafana** for observability

**Domain**: nozzly.app (configurable)

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

---

## 📝 License

This project will be open-sourced under MIT or Apache 2.0 license once MVP is complete.

**Current Status**: Private repository during initial development.

---

## 🙏 Acknowledgments

### Inspiration

- The 3D printing community for endless creativity
- Personal need for better business management tools
- Open source projects that make this possible

### Technologies

Built with amazing open source technologies:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [PostgreSQL](https://www.postgresql.org/)
- [shadcn/ui](https://ui.shadcn.com/)
- [OpenTelemetry](https://opentelemetry.io/)
- [k3s](https://k3s.io/)
- [Grafana](https://grafana.com/)

---

## 📧 Contact

**Project Owner**: Jonathan
**Domain**: [nozzly.app](https://nozzly.app)
**Repository**: [github.com/techize/nozzly.app](https://github.com/techize/nozzly.app)

---

## 🗺️ Vision

**Short Term**: Build a robust system for personal 3D printing business management
**Medium Term**: Open source and gather community feedback
**Long Term**: Become the go-to platform for 3D printing businesses of all sizes

**Monetization**: TBD (potential: managed hosting, premium integrations, support contracts)

---

**Made with ❤️ for the 3D printing community**

---

*Last Updated: 2025-11-13*
*Version: 0.2.0-alpha*
*Status: In Development - Phase 4 (Production Run System)*
