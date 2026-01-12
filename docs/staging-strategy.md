# Staging Environment Strategy

**Decision**: Same PostgreSQL instance, separate database (Option B)

## Rationale

Given this is a homelab k3s cluster with limited resources, using a separate database within the same PostgreSQL instance provides:

1. **Database-level isolation** - Separate schemas, data, can test migrations
2. **Resource efficiency** - No additional PostgreSQL StatefulSet overhead
3. **Simple management** - Single PostgreSQL to backup/maintain
4. **Migration safety** - Can run `alembic upgrade head` on staging before production

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL StatefulSet                    │
│                      (postgres:16-alpine)                    │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │   batchivo (prod)     │  │  batchivo_staging     │          │
│  │   - tenants         │  │  - tenants          │          │
│  │   - users           │  │  - users            │          │
│  │   - products        │  │  - products         │          │
│  │   - orders          │  │  - orders           │          │
│  └─────────────────────┘  └─────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
              │                        │
              ▼                        ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│  batchivo namespace   │  │  batchivo-staging namespace       │
│  (production)       │  │                                 │
│  - backend (x2)     │  │  - backend (x1)                 │
│  - frontend         │  │  - frontend                     │
│  - redis            │  │  - redis (shared or separate)   │
│  - minio            │  │  - minio (shared bucket prefix) │
└─────────────────────┘  └─────────────────────────────────┘
```

## Implementation Steps

### 1. Create staging database

```bash
# Connect to PostgreSQL pod
kubectl exec -it postgres-0 -n batchivo -- psql -U batchivo

# Create staging database
CREATE DATABASE batchivo_staging;

# Grant permissions
GRANT ALL PRIVILEGES ON DATABASE batchivo_staging TO batchivo;
```

### 2. Create batchivo-staging namespace

```yaml
# infrastructure/k8s/staging/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: batchivo-staging
  labels:
    environment: staging
```

### 3. Staging ConfigMap

Key differences from production:
- `DB_NAME: batchivo_staging`
- `ENVIRONMENT: staging`
- `CORS_ORIGINS` includes staging domains
- `STORAGE_S3_BUCKET: batchivo-staging-images` (separate bucket)

### 4. Staging secrets

Create separate secrets in batchivo-staging namespace:
- `postgres-secret` - same credentials, different DB_NAME
- `backend-secrets` - can use same JWT secret or separate
- `minio-credentials` - same MinIO, different bucket

### 5. DNS/Domains (covered by bead 86i)

- `staging.batchivo.app` → staging frontend
- `api.staging.batchivo.app` → staging backend
- `staging.mystmereforge.co.uk` → staging shop

## Seed Data Strategy

For staging tenant (covered by bead 5va):
1. Create "mystmereforge-staging" tenant
2. Copy subset of production data (products, categories)
3. Create test customer accounts
4. Generate sample orders for testing

## Migration Workflow

```bash
# 1. Deploy to staging first
kubectl set image deployment/backend backend=registry.techize.co.uk/batchivo/batchivo-backend:$SHA -n batchivo-staging

# 2. Verify migrations ran successfully
kubectl logs -l app=backend -n batchivo-staging --tail=50

# 3. Test staging environment
# - Run automated tests
# - Manual smoke test

# 4. Deploy to production
kubectl set image deployment/backend backend=registry.techize.co.uk/batchivo/batchivo-backend:$SHA -n batchivo
```

## Resource Requirements

Additional resources for staging:
- Backend: 1 replica (256Mi RAM, 250m CPU)
- Frontend: 1 replica (128Mi RAM, 100m CPU)
- Redis: Can share production Redis with key prefix, or 1 small replica
- MinIO: Share instance, use `batchivo-staging-images` bucket

**Total additional**: ~400Mi RAM, ~350m CPU

## Trade-offs

**Pros:**
- Low resource overhead
- Can test migrations before production
- Isolated data (separate database)
- Single PostgreSQL to maintain

**Cons:**
- Cannot test PostgreSQL version upgrades
- Cannot test destructive PostgreSQL operations
- Shared PostgreSQL performance (minimal impact)

## Future Consideration

If PostgreSQL-level testing becomes necessary:
- Add separate PostgreSQL StatefulSet for staging
- Use smaller resource allocation (128Mi/100m)
- Consider managed PostgreSQL if scaling beyond homelab
