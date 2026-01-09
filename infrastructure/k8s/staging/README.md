# Nozzly Staging Environment

Staging environment for testing changes before production deployment.

## Architecture

- **Namespace**: `nozzly-staging`
- **Database**: `nozzly_staging` (in shared PostgreSQL)
- **Redis**: Shared with production (database 1)
- **MinIO**: Shared with production (separate bucket)

## Setup

### 1. Create namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create secrets

Secrets must be created manually (not in git):

```bash
# PostgreSQL credentials (same user, different database)
kubectl create secret generic postgres-secret -n nozzly-staging \
  --from-literal=POSTGRES_USER=nozzly \
  --from-literal=POSTGRES_PASSWORD=<SAME_AS_PRODUCTION>

# Backend secrets
kubectl create secret generic backend-secrets -n nozzly-staging \
  --from-literal=SECRET_KEY=<GENERATE_NEW_SECRET>

# MinIO credentials (same as production)
kubectl create secret generic minio-credentials -n nozzly-staging \
  --from-literal=MINIO_ROOT_USER=<SAME_AS_PRODUCTION> \
  --from-literal=MINIO_ROOT_PASSWORD=<SAME_AS_PRODUCTION>

# Harbor registry credentials
kubectl create secret docker-registry harbor-creds -n nozzly-staging \
  --docker-server=registry.techize.co.uk \
  --docker-username=<USERNAME> \
  --docker-password=<PASSWORD>

# Square credentials (use sandbox keys for staging)
kubectl create secret generic square-credentials -n nozzly-staging \
  --from-literal=SQUARE_ACCESS_TOKEN=<SANDBOX_TOKEN> \
  --from-literal=SQUARE_ENVIRONMENT=sandbox \
  --from-literal=SQUARE_APPLICATION_ID=<SANDBOX_APP_ID> \
  --from-literal=SQUARE_LOCATION_ID=<SANDBOX_LOCATION_ID>

# Resend credentials
kubectl create secret generic resend-credentials -n nozzly-staging \
  --from-literal=RESEND_API_KEY=<STAGING_KEY>
```

### 3. Create staging MinIO bucket

```bash
kubectl exec -it minio-0 -n nozzly -- mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
kubectl exec -it minio-0 -n nozzly -- mc mb local/nozzly-staging-images
kubectl exec -it minio-0 -n nozzly -- mc anonymous set download local/nozzly-staging-images
```

### 4. Apply remaining resources

```bash
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml  # Created by bead l8z
```

## Database

The staging database was created with:

```sql
CREATE DATABASE nozzly_staging;
GRANT ALL PRIVILEGES ON DATABASE nozzly_staging TO nozzly;
```

Migrations run automatically via init container when backend deploys.

## Domains

- **Backend API**: `staging.nozzly.app` ✓
- **Shop Frontend**: `staging.mystmereforge.co.uk` ✓

Both domains route through Cloudflare Tunnel to Traefik.

### Cloudflare Tunnel Configuration

The cluster uses Cloudflare Tunnel for ingress. To add staging domains:

1. **Login to Cloudflare Dashboard**
   - Go to Zero Trust → Access → Tunnels
   - Select the nozzly tunnel

2. **Add Public Hostname for staging.nozzly.app**
   ```
   Subdomain: staging
   Domain: nozzly.app
   Type: HTTP
   URL: http://traefik.traefik.svc.cluster.local:80
   ```

3. **Add Public Hostname for staging.mystmereforge.co.uk** (when shop is deployed)
   ```
   Subdomain: staging
   Domain: mystmereforge.co.uk
   Type: HTTP
   URL: http://traefik.traefik.svc.cluster.local:80
   ```

SSL is automatically handled by Cloudflare.

## Deployment

Staging deploys before production in CI/CD pipeline:

```bash
# Deploy to staging
kubectl set image deployment/backend \
  backend=registry.techize.co.uk/nozzly/nozzly-backend:$SHA \
  -n nozzly-staging

# Verify staging
curl https://staging.nozzly.app/health

# Deploy to production
kubectl set image deployment/backend \
  backend=registry.techize.co.uk/nozzly/nozzly-backend:$SHA \
  -n nozzly
```

## Configuration Management

### Environment Differences

| Config | Production | Staging |
|--------|------------|---------|
| Database | `nozzly` | `nozzly_staging` |
| Redis DB | 0 | 1 |
| MinIO bucket | `nozzly-images` | `nozzly-staging-images` |
| Log level | INFO | DEBUG |
| CORS origins | Production domains | Staging domains |
| Square env | production | sandbox |

### ConfigMaps

- `backend-config`: All non-sensitive backend settings (see `configmap.yaml`)
- `frontend-config`: Frontend environment variables

### Secrets Status

| Secret | Status | Notes |
|--------|--------|-------|
| `postgres-secret` | ✓ Created | Same user, staging DB |
| `backend-secrets` | ✓ Created | Separate SECRET_KEY |
| `minio-credentials` | ✓ Created | Same as production |
| `harbor-creds` | ✓ Created | nozzly project access |
| `harbor-creds-mystmereforge` | ✓ Created | mystmereforge project access |
| `resend-credentials` | ✓ Created | Same API key as production |
| `square-credentials` | ⚠️ Optional | Needs Square sandbox credentials |

### Square Sandbox Setup (Optional)

For payment testing in staging, create Square sandbox credentials:

1. Go to [Square Developer Dashboard](https://developer.squareup.com/apps)
2. Select your application
3. Go to Sandbox settings
4. Copy sandbox credentials
5. Create the secret:

```bash
kubectl create secret generic square-credentials -n nozzly-staging \
  --from-literal=SQUARE_ACCESS_TOKEN=<SANDBOX_ACCESS_TOKEN> \
  --from-literal=SQUARE_ENVIRONMENT=sandbox \
  --from-literal=SQUARE_APP_ID=<SANDBOX_APP_ID> \
  --from-literal=SQUARE_LOCATION_ID=<SANDBOX_LOCATION_ID> \
  --from-literal=SQUARE_WEBHOOK_SIGNATURE_KEY=<SANDBOX_WEBHOOK_KEY>
```

Without this secret, payment features are disabled in staging (secret is marked optional).

### Shop Frontend Configuration

The mystmereforge-shop frontend has `VITE_NOZZLY_API_URL` baked in at build time.
Current staging uses production image, so API calls go to `api.nozzly.app`.

For true staging isolation, CI needs to build staging-specific images:
```bash
VITE_NOZZLY_API_URL=https://staging.nozzly.app npm run build
```

## CI/CD Pipeline

Both nozzly.app and mystmereforge-shop use a "staging-first" deployment strategy:

```
Push to main
    │
    ├─► Build & Test
    │
    ├─► Deploy to STAGING
    │       ↓
    ├─► Health Check Staging (2 min timeout)
    │       ↓
    └─► Deploy to PRODUCTION
```

### nozzly-backend Pipeline

On push to main branch:
1. Runs tests and security scans
2. Builds Docker image (`registry.techize.co.uk/nozzly/nozzly-backend:$SHA`)
3. Updates `infrastructure/k8s/staging/deployment.yaml`
4. Waits for staging health check at `https://staging.nozzly.app/health`
5. Updates `infrastructure/k8s/backend/deployment.yaml` (production)

### mystmereforge-shop Pipeline

On push to main branch:
1. Runs tests
2. Builds **staging** image with `VITE_NOZZLY_API_URL=https://staging.nozzly.app`
   - Tag: `$SHA-staging`
   - Uses Square sandbox credentials
3. Updates `infrastructure/k8s/staging/shop-deployment.yaml` (in nozzly.app repo)
4. Waits for staging health check at `https://staging.mystmereforge.co.uk/health`
5. Builds **production** image with `VITE_NOZZLY_API_URL=https://api.nozzly.app`
   - Tag: `$SHA` + `latest`
   - Uses Square production credentials
6. Updates `k8s/deployment.yaml` (in mystmereforge-shop repo)

### Woodpecker Secrets Required

For mystmereforge-shop staging deployment:
- `vite_square_app_id_sandbox` - Square sandbox app ID
- `vite_square_location_id_sandbox` - Square sandbox location ID

These use Square sandbox environment for staging payment testing.
