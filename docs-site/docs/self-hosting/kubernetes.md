---
sidebar_position: 3
---

# Kubernetes

Deploy Batchivo on Kubernetes for production-grade scalability.

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- Helm 3 (optional, for charts)

## Quick Start

```bash
# Apply namespace
kubectl apply -f infrastructure/k8s/namespace.yaml

# Create secrets
kubectl create secret generic backend-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -base64 64) \
  --from-literal=DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/batchivo \
  -n batchivo

# Apply all manifests
kubectl apply -f infrastructure/k8s/ -n batchivo
```

## Manifests

### Namespace

```yaml
# infrastructure/k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: batchivo
```

### Backend Deployment

```yaml
# infrastructure/k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: batchivo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/techize/batchivo-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: backend-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Frontend Deployment

```yaml
# infrastructure/k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: batchivo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: ghcr.io/techize/batchivo-frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
```

### Services

```yaml
# infrastructure/k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: batchivo
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: batchivo
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
```

## Ingress

### nginx Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: batchivo
  namespace: batchivo
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - batchivo.example.com
    secretName: batchivo-tls
  rules:
  - host: batchivo.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

## Database

For production, use a managed PostgreSQL service or deploy PostgreSQL with persistent storage.

### PostgreSQL StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: batchivo
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: batchivo
        - name: POSTGRES_USER
          value: batchivo
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: password
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

## Monitoring

Batchivo exposes Prometheus metrics at `/metrics` when `ENABLE_METRICS=true`.

```yaml
# ServiceMonitor for Prometheus Operator
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: batchivo-backend
  namespace: batchivo
spec:
  selector:
    matchLabels:
      app: backend
  endpoints:
  - port: http
    path: /metrics
```
