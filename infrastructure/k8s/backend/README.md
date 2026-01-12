# Backend Kubernetes Deployment

## Prerequisites

- Kubernetes cluster with `batchivo` namespace
- PostgreSQL database deployed (see `../postgres/`)
- Redis deployed (see `../redis/`)

## Secrets Management

**CRITICAL**: Secrets are NOT stored in git. You must create them manually before deploying.

### Creating Secrets

1. **Copy the template**:
   ```bash
   cp secrets.yaml.template secrets.yaml
   ```

2. **Generate JWT secret**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
   Copy the output and replace `SECRET_KEY` value in `secrets.yaml`

3. **Get Square credentials**:
   - Visit https://developer.squareup.com/apps
   - For **sandbox**: Use sandbox access token and location ID
   - For **production**: Use production credentials (requires approval)
   - Replace `SQUARE_ACCESS_TOKEN`, `SQUARE_LOCATION_ID`, and `SQUARE_ENVIRONMENT` in `secrets.yaml`

4. **Get Authentik credentials**:
   - From your Authentik admin panel
   - Replace `AUTHENTIK_CLIENT_ID` and `AUTHENTIK_CLIENT_SECRET` in `secrets.yaml`

5. **Apply secrets to cluster**:
   ```bash
   kubectl apply -f secrets.yaml
   ```

6. **Verify**:
   ```bash
   kubectl get secret backend-secrets -n batchivo
   kubectl describe secret backend-secrets -n batchivo
   ```

### Security Best Practices

- ✅ **DO**: Store `secrets.yaml` in a secure password manager (1Password, Bitwarden, etc.)
- ✅ **DO**: Use different secrets for dev, staging, and production
- ✅ **DO**: Rotate JWT secret periodically (will invalidate all sessions)
- ❌ **DON'T**: Commit `secrets.yaml` to git (already in `.gitignore`)
- ❌ **DON'T**: Share secrets via email, Slack, or other insecure channels
- ❌ **DON'T**: Use the same SECRET_KEY in multiple environments

## Deployment

### Initial Deployment

```bash
# 1. Apply secrets (see above)
kubectl apply -f secrets.yaml

# 2. Apply deployment
kubectl apply -f deployment.yaml

# 3. Verify
kubectl get pods -n batchivo
kubectl logs -n batchivo -l app=backend
```

### Updates

```bash
# Update deployment
kubectl apply -f deployment.yaml

# Verify rollout
kubectl rollout status deployment/backend -n batchivo

# View logs
kubectl logs -n batchivo -l app=backend --tail=100 -f
```

### Rolling Back

```bash
# View rollout history
kubectl rollout history deployment/backend -n batchivo

# Rollback to previous version
kubectl rollout undo deployment/backend -n batchivo

# Rollback to specific revision
kubectl rollout undo deployment/backend -n batchivo --to-revision=2
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -n batchivo

# Describe pod for events
kubectl describe pod <pod-name> -n batchivo

# Check logs
kubectl logs <pod-name> -n batchivo

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n batchivo --previous
```

### Database connection issues

```bash
# Test database connectivity from pod
kubectl exec -it <pod-name> -n batchivo -- psql $DATABASE_URL -c "SELECT 1"

# Check if postgres service is running
kubectl get svc postgres -n batchivo
kubectl get pods -n batchivo -l app=postgres
```

### Secret not found errors

```bash
# Verify secret exists
kubectl get secret backend-secrets -n batchivo

# If missing, create it (see "Creating Secrets" above)
kubectl apply -f secrets.yaml

# Restart deployment
kubectl rollout restart deployment/backend -n batchivo
```

## Database Credentials

**IMPORTANT**: The database password is stored in `postgres-secret` and NOT in any committed files.

### Creating/Updating Database Secret

```bash
# Create postgres-secret with secure password
kubectl create secret generic postgres-secret -n batchivo \
  --from-literal=POSTGRES_USER=batchivo \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=POSTGRES_DB=batchivo

# Or update existing secret
kubectl delete secret postgres-secret -n batchivo
kubectl create secret generic postgres-secret -n batchivo \
  --from-literal=POSTGRES_USER=batchivo \
  --from-literal=POSTGRES_PASSWORD=<YOUR_NEW_PASSWORD> \
  --from-literal=POSTGRES_DB=batchivo

# Restart deployments to pick up new credentials
kubectl rollout restart statefulset/postgres -n batchivo
kubectl rollout restart deployment/backend -n batchivo
```

The `DATABASE_URL` is automatically constructed from:
- `postgres-secret`: POSTGRES_USER, POSTGRES_PASSWORD
- `backend-config`: DB_HOST, DB_PORT, DB_NAME

## Environment Variables

Environment variables are sourced from:

1. **ConfigMap** (`backend-config`): Non-sensitive configuration
   - DB_HOST, DB_PORT, DB_NAME (database connection params)
   - REDIS_URL
   - ENVIRONMENT
   - LOG_LEVEL
   - CORS_ORIGINS
   - etc.

2. **Secret** (`postgres-secret`): Database credentials
   - POSTGRES_USER
   - POSTGRES_PASSWORD
   - POSTGRES_DB

3. **Secret** (`backend-secrets`): Other sensitive credentials
   - SECRET_KEY (JWT signing)

4. **Secret** (`square-credentials`): Payment provider
   - SQUARE_ACCESS_TOKEN
   - SQUARE_LOCATION_ID
   - etc.

## Health Checks

The deployment includes liveness and readiness probes:

- **Liveness**: `/health` endpoint (fails → container restart)
- **Readiness**: `/health` endpoint (fails → removed from service)

Check health endpoint:
```bash
kubectl port-forward svc/backend 8000:8000 -n batchivo
curl http://localhost:8000/health
```

## Resource Limits

Current configuration:
- **Requests**: 256Mi memory, 250m CPU
- **Limits**: 512Mi memory, 500m CPU

Adjust in `deployment.yaml` if needed based on observed usage.

## Horizontal Pod Autoscaling

To enable HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: batchivo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Apply with:
```bash
kubectl apply -f hpa.yaml
kubectl get hpa -n batchivo
```
