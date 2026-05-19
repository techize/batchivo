# Batchivo - 3D Print Business Management Platform

## Critical Rules (MANDATORY)

### Deployment
**Only workflow for deploying changes:**
1. Push to GitHub (main branch)
2. Woodpecker CI builds Docker images → pushes to k3s registry
3. ArgoCD auto-syncs within 3 minutes

**NEVER manually build/push Docker images. NEVER `kubectl apply` directly.**

- **CI**: https://ci.techize.co.uk (Woodpecker)
- **CD**: https://argocd.techize.co.uk (ArgoCD)
- **Registry**: `192.168.98.138:30500`

### Branch & Commit
- Direct to main (current strategy)
- Commit style: `type: description` (e.g., `fix:`, `feat:`, `docs:`)
- No AI markers or Co-Authored-By in commits

### Code Quality
- **All code MUST have tests** — no exceptions
- Before committing: `cd backend && poetry run pytest && poetry run ruff check`
- Frontend: `cd frontend && npm test && npm run lint`

### Multi-Tenant Security
- Every table has `tenant_id` — **NEVER** query without tenant scope
- Use `get_current_tenant()` dependency in all endpoints
- PostgreSQL RLS enforces isolation at database level

```python
@router.get("/items")
async def list_items(
    tenant: Tenant = Depends(get_current_tenant),  # REQUIRED
    db: AsyncSession = Depends(get_db)
):
    pass  # Queries auto-scoped via RLS
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Backend dev | `cd backend && poetry run uvicorn app.main:app --reload` |
| Frontend dev | `cd frontend && npm run dev` |
| Run tests | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |
| Lint | `cd backend && poetry run ruff check && poetry run ruff format --check` |
| DB migrate | `cd backend && poetry run alembic upgrade head` |
| New migration | `cd backend && poetry run alembic revision --autogenerate -m "description"` |

| Production | Command |
|------------|---------|
| Check pods | `kubectl get pods -n batchivo` |
| Backend logs | `kubectl logs -l app=backend -n batchivo -f` |
| Frontend logs | `kubectl logs -l app=frontend -n batchivo -f` |
| ArgoCD sync | `argocd app sync batchivo-app` |
| Rollback | `argocd app rollback batchivo-app` |
| Verify health | `curl https://api.batchivo.com/health` |

---

## Architecture

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL | React 18 + TypeScript + TanStack Query + shadcn/ui | k3s + ArgoCD + Cloudflare Tunnel | Custom JWT auth

**URLs:**
- Admin/API: www.batchivo.com / api.batchivo.com
- Shop: test.mystmereforge.co.uk → mystmereforge-shop repo

---

## Testing Policy

| Change Type | Required Tests |
|-------------|----------------|
| New endpoint | Success (200/201), auth (401), validation (422), not found (404) |
| Business logic | Success path, edge cases, error conditions |
| Bug fix | Regression test proving fix works |
| Schema change | Model CRUD, relationships, constraints |

**Available fixtures:** `client`, `db_session`, `test_tenant`, `test_user`, `test_spool`

---

## Integrations

### Square (Payments)
- Secret: `kubectl get secret square-credentials -n batchivo`
- Webhook: `https://api.batchivo.com/api/v1/payments/webhooks/square`
- Events: `payment.created`, `payment.updated`, `refund.created`, `refund.updated`
- Status: sandbox credentials active — switch to production when ready

### Resend (Email)
- Secret: `kubectl get secret resend-credentials -n batchivo`
- From: orders@mystmereforge.co.uk
- Service: `backend/app/services/email_service.py`
- Status: production credentials active, sends order confirmation emails

---

## Troubleshooting

```bash
# Pod not starting
kubectl describe pod <pod-name> -n batchivo
kubectl logs <pod-name> -n batchivo --previous

# Database shell
kubectl exec -it postgres-0 -n batchivo -- psql -U batchivo -d batchivo

# ArgoCD out of sync
argocd app sync batchivo-app --prune
```
