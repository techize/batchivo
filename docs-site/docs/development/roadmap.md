---
sidebar_position: 4
---

# Roadmap

Planned features and development priorities for Batchivo.

## Current Status

**Version**: 0.1.0 (Alpha)

Batchivo is under active development. Core functionality is being built and tested.

## Completed

### Phase 1: Foundation
- [x] Project structure and infrastructure
- [x] Multi-tenant architecture with RLS
- [x] JWT authentication with refresh tokens
- [x] Full observability stack (OpenTelemetry)
- [x] Backend deployment (k3s)
- [x] Frontend deployment (Cloudflare)

### Phase 2: Inventory Management
- [x] Spool database models
- [x] Spool CRUD API
- [x] Spool frontend UI
- [x] Material types and colors
- [x] Weight tracking

### Phase 3: Product Catalog
- [x] Product database models
- [x] Multi-material BOM
- [x] Product API endpoints
- [x] Cost calculation service
- [x] Product frontend UI

### Phase 4: Production Runs (Partial)
- [x] Production run models
- [x] Multi-product bed support
- [x] Spool weighing
- [x] Variance analysis

## In Progress

### Phase 4: Production Runs (Completion)
- [ ] Production run API endpoints
- [ ] Production run frontend UI
- [ ] Inventory deduction on completion

### Documentation
- [x] Self-hosting guide
- [x] API reference
- [ ] Video tutorials
- [ ] User guide completion

## Planned

### Phase 5: Orders & Sales
- [ ] Order management
- [ ] Customer database
- [ ] Invoice generation
- [ ] Marketplace integrations (Etsy, eBay)

### Phase 6: Analytics & Reporting
- [ ] Dashboard with KPIs
- [ ] Profitability reports
- [ ] Material usage analytics
- [ ] Production efficiency metrics

### Phase 7: Advanced Features
- [ ] Printer integration (OctoPrint, Bambu)
- [ ] G-code analysis for estimates
- [ ] QR code spool tracking
- [ ] Mobile app (spool weighing)

### Phase 8: Collaboration
- [ ] Team management
- [ ] Role-based permissions
- [ ] Activity audit log
- [ ] Shared workspaces

## Feature Requests

Have an idea? Share it in [GitHub Discussions](https://github.com/techize/batchivo/discussions/categories/ideas).

Popular requests:

- [ ] Marketplace sync (auto-list products)
- [ ] Shipping label integration
- [ ] Accounting export (QuickBooks, Xero)
- [ ] Print farm management
- [ ] Customer portal

## Release Schedule

We aim for regular releases:

- **Patch releases**: As needed for bug fixes
- **Minor releases**: Monthly with new features
- **Major releases**: When breaking changes required

## Contributing

Want to help build a feature? See the [Contributing Guide](/docs/development/contributing).

Priority areas:

1. Production run UI
2. Dashboard components
3. Documentation
4. Test coverage

## Versioning

Batchivo follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## Deprecation Policy

- Deprecated features announced in release notes
- Minimum 2 minor versions before removal
- Migration guides provided
