# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open source release preparation
  - LICENSE file (MIT)
  - CONTRIBUTING.md with contribution guidelines
  - SECURITY.md with vulnerability reporting process
  - VERSIONING.md with semantic versioning strategy
  - This CHANGELOG

### Fixed
- Backend Docker health check now uses stdlib `urllib.request` instead of missing `requests` dependency

---

## [0.2.0-alpha] - 2026-01-14

### Added
- **Etsy Integration** (Phase 5 preview)
  - Etsy API v3 integration with OAuth2
  - "Sync to Etsy" button on product pages
  - External listing tracking
  - Listing sync status display

- **Product Enhancements**
  - Product specification fields (dimensions, weight, materials)
  - External listing management
  - Improved product detail views

- **Infrastructure**
  - Runtime config support for frontend (dynamic API URL)
  - Staging environment configuration
  - Improved ArgoCD deployment configuration

### Changed
- Complete rebrand from Nozzly to Batchivo
  - New domain: batchivo.com
  - Updated color system and typography
  - New logo and brand assets
  - Renamed all packages and configurations

### Fixed
- FastAPI dependency injection for Etsy sync endpoint
- PostgreSQL data permissions with init container
- Staging health check soft failure handling

---

## [0.1.0] - 2026-01-09

### Added
- **Phase 1: Foundation & Authentication** (Complete)
  - Multi-tenant architecture with Row-Level Security (RLS)
  - Custom JWT authentication with secure refresh tokens
  - Full observability stack (OpenTelemetry, Prometheus, Grafana, Tempo, Loki)
  - Backend deployment on k3s cluster
  - Frontend deployment with Cloudflare ingress

- **Phase 2: Inventory Management** (Partial)
  - Filament spool database models and migrations
  - Spool API endpoints (CRUD, filtering, search)
  - Spool frontend components (list, detail, create, edit forms)
  - Material types and color tracking
  - Weight tracking and purchase history

- **Phase 3: Product Catalog & Costing** (Partial)
  - Product database models (Product, ProductMaterial, ProductComponent)
  - Product API endpoints with comprehensive costing
  - Product frontend components (list, create, edit)
  - Multi-material Bill of Materials (BOM)
  - Component cost tracking
  - Labor and overhead allocation

- **Phase 4: Production Run System** (In Progress)
  - Production run database models
  - Initial API structure

### Technical Foundation
- FastAPI 0.124+ backend with async SQLAlchemy 2.0
- React 18+ frontend with TypeScript 5.0+
- TanStack Query for server state management
- shadcn/ui component library
- PostgreSQL with Row-Level Security
- Redis for caching and Celery task queue
- Kubernetes deployment with ArgoCD
- Woodpecker CI for continuous integration

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 0.2.0-alpha | 2026-01-14 | Current |
| 0.1.0 | 2026-01-09 | Initial fork |

---

[Unreleased]: https://github.com/techize/batchivo/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/techize/batchivo/compare/v0.1.0...v0.2.0-alpha
[0.1.0]: https://github.com/techize/batchivo/releases/tag/v0.1.0
