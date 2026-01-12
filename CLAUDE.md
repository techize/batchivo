# Batchivo - 3D Print Business Management Platform

## Critical Rules (MANDATORY)

### Git & Deployment Workflow
**This is the ONLY workflow for deploying changes:**
1. Push to GitHub (main branch or PR)
2. Woodpecker CI builds Docker images → pushes to k3s registry (`192.168.98.138:30500`)
3. ArgoCD auto-syncs within 3 minutes

**CI/CD Infrastructure (Homelab k3s cluster):**
- **CI**: Woodpecker CI at https://ci.techize.co.uk
- **CD**: ArgoCD at https://argocd.techize.co.uk
- **Registry**: `192.168.98.138:30500` (in-cluster Docker registry)
- **GitHub**: Repository hosting only (NOT GitHub Actions)

**NEVER manually build/push Docker images. NEVER kubectl apply directly.**

**Branch Strategy:**
- **Current**: Direct to main (hotfixes only - temporary)
- **TODO**: Implement branch + PR workflow for production changes
- Commit style: `type: description` (e.g., `fix:`, `feat:`, `docs:`)
- No AI markers or Co-Authored-By in commits

### Code Quality
- **All code MUST have tests** - No exceptions (see Testing section)
- Run before committing: `cd backend && poetry run pytest && poetry run ruff check`
- Frontend: `cd frontend && npm test && npm run lint`

### Multi-Tenant Security
- Every table has `tenant_id` - **NEVER** query without tenant scope
- Use `get_current_tenant()` dependency in all endpoints
- PostgreSQL RLS enforces isolation at database level

---

## Quick Reference

| Action | Command |
|--------|---------|
| Backend dev | `cd backend && poetry run uvicorn app.main:app --reload` |
| Frontend dev | `cd frontend && npm run dev` |
| Run tests | `cd backend && poetry run pytest --cov=app` |
| Lint | `cd backend && poetry run ruff check && poetry run ruff format --check` |
| DB migrate | `cd backend && poetry run alembic upgrade head` |
| New migration | `cd backend && poetry run alembic revision --autogenerate -m "description"` |

**Production:**
| Action | Command |
|--------|---------|
| Check pods | `kubectl get pods -n batchivo` |
| Backend logs | `kubectl logs -l app=backend -n batchivo -f` |
| Frontend logs | `kubectl logs -l app=frontend -n batchivo -f` |
| ArgoCD sync | `argocd app sync batchivo-app` |
| Rollback | `argocd app rollback batchivo-app` |

---

## Architecture

### Tech Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL
- **Frontend**: React 18 + TypeScript + TanStack Query + shadcn/ui
- **Infra**: k3s + ArgoCD + Cloudflare Tunnel
- **Auth**: Custom JWT (bcrypt + refresh tokens)

### Directory Structure
```
backend/
├── app/
│   ├── api/v1/        # API endpoints
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── main.py        # FastAPI app
├── alembic/           # Migrations
└── tests/             # Pytest tests

frontend/
├── src/
│   ├── components/    # React components
│   ├── lib/api/       # API client
│   ├── hooks/         # Custom hooks
│   └── types/         # TypeScript types

infrastructure/k8s/    # Kubernetes manifests (ArgoCD watches this)
```

### Key Patterns
```python
# All API endpoints follow this pattern:
@router.get("/items")
async def list_items(
    tenant: Tenant = Depends(get_current_tenant),  # REQUIRED
    db: AsyncSession = Depends(get_db)
):
    # Queries auto-scoped via RLS
```

---

## Testing Policy

**Every change MUST include tests:**

| Change Type | Required Tests |
|-------------|----------------|
| New endpoint | Success (200/201), auth (401), validation (422), not found (404) |
| Business logic | Success path, edge cases, error conditions |
| Bug fix | Regression test proving fix works |
| Schema change | Model CRUD, relationships, constraints |

**Test fixtures available:** `client`, `db_session`, `test_tenant`, `test_user`, `test_spool`

```bash
# Run with coverage
poetry run pytest --cov=app --cov-report=term-missing
```

---

## Development Workflow

### Before Starting Work
1. `git pull origin main`
2. Check ArgoCD status: `argocd app get batchivo-app`
3. Ensure tests pass: `cd backend && poetry run pytest`

### Making Changes
1. Write tests alongside code
2. Run `poetry run pytest && poetry run ruff check`
3. Commit: `git commit -m "type: description"`
4. Push: `git push origin main`
5. Woodpecker CI builds → ArgoCD syncs automatically

### After Deployment
- Check pods: `kubectl get pods -n batchivo`
- Watch logs: `kubectl logs -l app=backend -n batchivo -f`
- Verify: `curl https://api.batchivo.app/health`

---

## Project Context

**Purpose**: Multi-tenant SaaS for 3D printing business management
- Inventory (filament spools, consumables)
- Products (with BOM, costing)
- Orders & Sales channels
- Production runs & analytics

**URLs:**
- **Admin/API**: www.batchivo.app / api.batchivo.app (Cloudflare Tunnel)
- **Shop Frontend**: test.mystmereforge.co.uk (future: www.mystmereforge.co.uk)
- **Shop Repo**: ~/Repos/mystmereforge-shop

**Infrastructure:**
- **Registry**: 192.168.98.138:30500 (k3s in-cluster)
- **Cluster**: Local k3s homelab

---

## Payment Integration (Square)

**Credentials stored in:** `kubectl get secret square-credentials -n batchivo`

| Environment Variable | Description |
|---------------------|-------------|
| `SQUARE_ACCESS_TOKEN` | API access token (sandbox or production) |
| `SQUARE_APP_ID` | Square application ID |
| `SQUARE_ENVIRONMENT` | `sandbox` or `production` |
| `SQUARE_LOCATION_ID` | Square location ID (needed for payments) |
| `SQUARE_WEBHOOK_SIGNATURE_KEY` | Webhook signature key for HMAC validation |

**Webhook Configuration:**
- **Subscription ID**: `wbhk_f1b36f197f714e9085e6ded8bc6fdcd9`
- **Endpoint**: `https://api.batchivo.app/api/v1/payments/webhooks/square`
- **Events**: `payment.created`, `payment.updated`, `refund.created`, `refund.updated`

**To update credentials:**
```bash
# Delete existing and recreate
kubectl delete secret square-credentials -n batchivo
kubectl create secret generic square-credentials -n batchivo \
  --from-literal=SQUARE_ACCESS_TOKEN=<token> \
  --from-literal=SQUARE_APP_ID=<app_id> \
  --from-literal=SQUARE_ENVIRONMENT=<sandbox|production> \
  --from-literal=SQUARE_LOCATION_ID=<location_id> \
  --from-literal=SQUARE_WEBHOOK_SIGNATURE_KEY=<signature_key>
```

**Status:** Sandbox credentials configured with webhook signature validation (Dec 2025). Switch to production when ready.

---

## Email Integration (Resend)

**Credentials stored in:** `kubectl get secret resend-credentials -n batchivo`

| Environment Variable | Description |
|---------------------|-------------|
| `RESEND_API_KEY` | Resend API key for transactional emails |

**Configuration in config.py:**
- `email_from_address`: orders@mystmereforge.co.uk
- `email_from_name`: Mystmereforge

**Email service location:** `backend/app/services/email_service.py`

**To update credentials:**
```bash
kubectl delete secret resend-credentials -n batchivo
kubectl create secret generic resend-credentials -n batchivo \
  --from-literal=RESEND_API_KEY=<api_key>
kubectl rollout restart deployment/backend -n batchivo
```

**Status:** Production credentials configured (Dec 2025). Sends order confirmation emails automatically.

---

## Detailed Documentation

For comprehensive information, see:
- `docs/DATABASE_SCHEMA.md` - Complete schema with RLS examples
- `docs/ARCHITECTURE.md` - System design details
- `docs/DEVELOPMENT.md` - Local setup guide
- `docs/API.md` - API endpoint documentation
- `.taskmaster/CLAUDE.md` - Task Master AI workflow

---

## Troubleshooting

**Pod not starting:**
```bash
kubectl describe pod <pod-name> -n batchivo
kubectl logs <pod-name> -n batchivo --previous
```

**Database issues:**
```bash
kubectl exec -it postgres-0 -n batchivo -- psql -U batchivo -d batchivo
```

**ArgoCD out of sync:**
```bash
argocd app sync batchivo-app --prune
```

---

*Last Updated: 2025-12-19*
