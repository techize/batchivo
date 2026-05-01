# Roadmap

Batchivo is in **0.2.0-alpha** and is currently in **pre-MVP hardening**. The core 3D printing business workflow is largely implemented; the remaining MVP work is about proving the workflow end to end, validating deployment, and triaging imported backlog items now that Beads is the source of truth.

Use `bd ready` for the live queue. This file is a phase-level map, not the issue tracker.

---

## MVP Definition

The MVP is a self-hosted 3D printing business system where a tenant can:

- Onboard, authenticate, and manage tenant settings
- Track filament, consumables, QR labels, and inventory adjustments
- Define products with BOMs, costs, images, categories, and variants
- Create and complete production runs with actual material usage and variance
- Manage orders, sales channels, customers, shipping, and basic payments
- Review dashboard, analytics, forecasting, and export data
- Deploy the stack with documented self-hosting steps
- Run the key happy paths through automated tests

---

## Phase 0: Project Control - Done

- [x] Beads initialized and documented in `AGENTS.md`
- [x] Task Master backlog imported into Beads
- [x] Stale Task Master source-of-truth references removed from status docs
- [x] Quality gates repaired after Beads migration
- [ ] Imported Beads issues fully triaged for stale descriptions and duplicate work

---

## Phase 1: Foundation - Done

- [x] FastAPI backend and React/TypeScript frontend
- [x] Multi-tenant architecture and tenant-aware APIs
- [x] Authentication, refresh tokens, onboarding, users, and tenant membership
- [x] Module system and tenant settings
- [x] Audit, exports, dashboard, analytics, and forecasting surfaces
- [x] Docker Compose local development
- [x] k3s/Cloudflare self-hosting assets

---

## Phase 2: Core 3D Print Operations - Mostly Done

- [x] Spool and consumable models, APIs, and UI
- [x] Material, brand, color, purchase, weight, location, and status tracking
- [x] QR code and label workflows
- [x] Product catalog with SKUs, images, categories, designers, BOMs, and costing
- [x] Product variants and size/capability groundwork
- [x] Production run APIs and frontend workflows
- [x] Multi-plate production runs, completion, reprints, quality, and variance analysis
- [x] Inventory transactions on production run completion
- [ ] E2E tests for the full inventory -> production -> order path

---

## Phase 3: Commerce And Fulfillment - Mostly Done

- [x] Orders, customers, sales channels, discounts, returns, and shipping rates
- [x] Public shop, shop resolver, customer authentication, and account surfaces
- [x] Square/payment configuration surfaces
- [x] Shopify sync and webhook groundwork
- [x] CSV/export flows
- [ ] Full order-processing E2E coverage (`batchivo-tm028`)
- [ ] Marketplace OAuth/order import for Etsy, eBay, and full Shopify automation
- [ ] Abandoned cart email reminder system (`batchivo-tm061`)

---

## Phase 4: MVP Hardening - In Progress

- [x] Backend and frontend test suites repaired after tracker migration
- [x] Documentation status refreshed against the implemented codebase
- [ ] Production deployment validation on a clean environment
- [ ] Wildcard DNS/domain configuration for self-hosted tenant routing (`batchivo-tm134`)
- [ ] Structured JSON logging and correlation IDs
- [ ] Prometheus alert rules and notification channels
- [ ] Final Beads triage: close stale imported tasks or split real remaining work

---

## Phase 5: Printer Automation - Post-MVP

- [x] Printer model/API foundations
- [x] Print queue and WebSocket status surfaces
- [x] Bambu integration surface
- [ ] OctoPrint integration
- [ ] Moonraker/Klipper integration
- [ ] Generic printer webhook processing
- [ ] Real-time printer fleet dashboard hardening
- [ ] AI failure detection integration

---

## Phase 6: Business Intelligence - Post-MVP

- [x] Dashboard and analytics API foundations
- [x] Forecasting surface
- [x] Export/reporting groundwork
- [ ] Complete COGS including depreciation, electricity, consumables, and labor
- [ ] Margin optimization and marketplace fee comparison
- [ ] Supplier/reorder automation
- [ ] Production and profitability reporting polish

---

## Phase 7: Multi-Craft Modules - Post-MVP

The imported backlog contains knitting tasks marked as complete in places, but the codebase does not yet have production-ready knitting APIs.

- [x] Knitting module definitions for yarn, needles, patterns, and projects
- [ ] Yarn API implementation beyond placeholder router
- [ ] Needle API implementation beyond placeholder router
- [ ] Pattern API router
- [ ] Project API router
- [ ] Tenant module integration tests for knitting routes
- [ ] Frontend workflows for knitting tenants

---

## Live Backlog

Use Beads for current work:

```bash
bd ready
bd show <id>
bd list --status open
```

As of 2026-05-01 after the Task Master migration and first triage pass: 384 total Beads issues, 36 open, 0 in progress, 345 closed, 15 blocked, 2 deferred, and 21 ready.
