# Roadmap

This document outlines the development roadmap for Batchivo. Features are organized by phase, with completed items marked.

## Current Status

**Version:** 0.2.0-alpha
**Stage:** Active Development

---

## Phase 1: Foundation ✅

Core infrastructure and authentication.

- [x] Project structure (FastAPI + React + TypeScript)
- [x] Multi-tenant architecture with Row-Level Security
- [x] JWT authentication with secure refresh tokens
- [x] Full observability stack (OpenTelemetry, Prometheus, Grafana)
- [x] Docker Compose development environment
- [x] Kubernetes deployment configuration

---

## Phase 2: Inventory Management ✅

Filament spool tracking and management.

- [x] Spool database models and migrations
- [x] Spool CRUD API endpoints with filtering
- [x] Spool frontend components
- [x] Material types, colors, brands tracking
- [x] Weight tracking and purchase history
- [ ] QR code generation and scanning
- [ ] Low stock alerts

---

## Phase 3: Product Catalog ✅

Product definitions and cost calculation.

- [x] Product database models
- [x] Multi-material Bill of Materials (BOM)
- [x] Component cost tracking (magnets, inserts, etc.)
- [x] Automatic cost calculation service
- [x] Product CRUD frontend
- [ ] Product images and galleries
- [ ] Product categories and tags

---

## Phase 4: Production Runs 🚧

Manufacturing tracking and variance analysis.

- [x] Production run database models
- [x] Batch printing support (multiple products per bed)
- [x] Multi-color print tracking with purge/waste
- [x] Spool weighing (before/after)
- [x] Variance analysis (estimated vs actual)
- [x] Quality rating and reprint tracking
- [ ] Production run API endpoints
- [ ] Production run frontend UI
- [ ] Automatic inventory deduction

---

## Phase 5: Pricing Engine 📋

Multi-marketplace pricing optimization.

- [ ] Marketplace fee calculators (Etsy, eBay, Shopify)
- [ ] Break-even analysis
- [ ] Target margin optimization
- [ ] Bulk pricing updates
- [ ] Price comparison across platforms

---

## Phase 6: Marketplace Integration 📋

Direct integration with selling platforms.

- [ ] Etsy API integration
- [ ] Square Online integration
- [ ] Inventory sync across platforms
- [ ] Order import and tracking
- [ ] Automatic listing updates

---

## Phase 7: Analytics & Reporting 📋

Business intelligence and insights.

- [ ] Production analytics dashboard
- [ ] Material usage reports
- [ ] Profitability analysis by product
- [ ] Trend visualization
- [ ] Export to CSV/Excel

---

## Future Considerations

Features under consideration for future releases:

- **Mobile app** - Spool scanning and quick production logging
- **Print farm management** - Multi-printer job scheduling
- **Supplier integration** - Auto-reorder from preferred suppliers
- **Community marketplace** - Share product templates and BOMs
- **AI cost optimization** - Suggest BOM improvements

---

## Contributing

Want to help build a feature? Check out our [Contributing Guide](CONTRIBUTING.md) and look for issues labeled `good first issue` or `help wanted`.

---

## Legend

- ✅ Phase complete
- 🚧 In progress
- 📋 Planned
