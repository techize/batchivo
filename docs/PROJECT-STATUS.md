# Batchivo Project Status

**Last updated:** 2026-05-01
**Version:** 0.2.0-alpha
**Stage:** Pre-MVP hardening
**Issue tracker:** Beads (`bd`)

---

## Source Of Truth

Beads is now the authoritative project tracker. The old Task Master backlog was migrated on 2026-05-01 and should be treated as historical metadata only.

```bash
bd ready
bd show <id>
bd update <id> --status in_progress
bd close <id> --reason "Completed"
bd export --output .beads/issues.jsonl
```

---

## Beads Snapshot

Snapshot after claiming the documentation refresh issue on 2026-05-01:

| Metric | Count |
|--------|-------|
| Total issues | 385 |
| Open | 36 |
| In progress | 0 |
| Closed | 346 |
| Blocked | 15 |
| Deferred | 2 |
| Ready | 21 |

Current blocked work:

| ID | Summary |
|----|---------|
| `batchivo-tm098` | Multi-tenant test coverage follow-up, blocked on real knitting CRUD APIs |

---

## MVP Status

Batchivo is close to an MVP for the core 3D printing workflow, but it is not yet landed. The implemented product is broader than the old roadmap suggested: production runs, product categories, images, variants, orders, shipping, public shop surfaces, analytics, exports, printer foundations, and Shopify groundwork all exist in code.

The remaining MVP work is mainly proof and hardening:

- Admin order creation/payment UI remains missing; current E2E coverage starts from an existing paid order (`batchivo-sc7p`)
- Clean production deployment validation, including wildcard DNS/domain routing (`batchivo-tm134`)
- Triage of imported Beads issues whose Task Master descriptions are stale
- Structured logging, alerting, and operational runbooks
- Final pass over user/developer docs for the exact MVP workflow

Knitting/multi-craft support is not part of the near-term 3D printing MVP. The module definitions exist, but yarn and needle routers are placeholders and pattern/project APIs are missing.

---

## Implemented Surfaces

### Platform Foundation

- FastAPI backend, React 19 frontend, TypeScript 5.9, Vite 7
- Multi-tenant onboarding, authentication, refresh tokens, tenant membership, users, settings, and module configuration
- Admin dashboard, audit, exports, analytics, forecasting, and platform routes
- Docker Compose, k3s manifests, Cloudflare self-hosting assets, and observability configuration

### Inventory And Catalog

- Spools, consumables, material attributes, purchase data, locations, and inventory transaction tracking
- QR code, label printing, scan, and quick update workflows
- Product catalog, SKUs, models, model files, BOMs, product costing, images, categories, designers, and variants

### Production

- Production run API and frontend workflows
- Multi-plate support, material usage, run completion, variance analysis, quality ratings, reprints, and production history
- Inventory adjustments connected to production completion
- Printer, print queue, Bambu, and WebSocket status foundations

### Commerce

- Orders, customers, sales channels, discounts, returns, shipping rates, public shop, shop resolver, customer auth/account, and reviews
- Square/payment settings surfaces
- Shopify sync and webhook groundwork
- Newsletter and export flows

---

## Known Gaps

| Area | Gap | Tracker |
|------|-----|---------|
| Order creation | Admin create-order/payment UI is not implemented; current order E2E covers admin processing after checkout | `batchivo-sc7p` |
| Deployment | Wildcard DNS/domain configuration needs implementation/validation | `batchivo-tm134` |
| Backlog hygiene | Imported Task Master items need stale/duplicate triage | Beads ready queue |
| Operations | Alert rules, structured JSON logging, correlation IDs, and runbooks need completion | `batchivo-tm032`, `batchivo-tm033` |
| Commerce automation | Abandoned cart emails and marketplace OAuth integrations remain open | `batchivo-tm061`, `batchivo-tm046` |
| Printer automation | OctoPrint, Moonraker/Klipper, generic webhooks, and live fleet hardening remain post-MVP | `batchivo-tm038`-`batchivo-tm043` |
| Multi-craft | Knitting API routers are placeholders and CRUD APIs are missing | `batchivo-tm086`-`batchivo-tm089`, `batchivo-tm098` |

---

## Verification Snapshot

Last verified during the Beads repair session on 2026-05-01:

| Gate | Result |
|------|--------|
| Backend tests | 3634 passed, 19 skipped |
| Frontend unit tests | 334 passed |
| Frontend production audit | 0 vulnerabilities |
| Landing build | Passed |

These numbers are a recent snapshot, not a substitute for running the gates before landing code changes.

---

## Recommended Next Work

1. Close this documentation refresh after review and export Beads state.
2. Implement the reopened knitting backend tasks `batchivo-tm086` through `batchivo-tm089`, then unblock `batchivo-tm098`.
3. Decide whether `batchivo-sc7p` is required for MVP or whether order creation remains shop/checkout-only.
4. Resolve deployment/domain issue `batchivo-tm134`.
5. Work through the remaining `bd ready` queue, closing stale imported issues where code already satisfies the acceptance criteria.
