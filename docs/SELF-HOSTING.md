# Self-Hosting Guide

Deploy Batchivo on your own infrastructure.

---

## Deployment Options

| Method | Complexity | Best For |
|--------|------------|----------|
| Docker Compose | Low | Single server, home lab |
| Kubernetes | Medium | Multi-node, production |
| Manual | High | Custom environments |

---

## Docker Compose (Recommended)

The simplest way to self-host Batchivo.

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Quick Start

```bash
# Clone repository
git clone https://github.com/gullinmedia/batchivo.git
cd batchivo

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env 2>/dev/null || true

# Edit backend/.env with your settings
# At minimum, set a secure SECRET_KEY:
# python -c "import secrets; print(secrets.token_urlsafe(64))"

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Production Docker Compose

For production, create a `docker-compose.prod.yml`:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: batchivo
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: batchivo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  backend:
    image: ghcr.io/gullinmedia/batchivo-backend:latest
    environment:
      DATABASE_URL: postgresql+psycopg://batchivo:${DB_PASSWORD}@postgres:5432/batchivo
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    image: ghcr.io/gullinmedia/batchivo-frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Start with:

```bash
# Set required environment variables
export DB_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Start
docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ chars) | `openssl rand -base64 64` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+psycopg://user:pass@host:5432/db` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `ENVIRONMENT` | Environment name | `development` |
| `CORS_ORIGINS` | Allowed origins | `["http://localhost:5173"]` |
| `ENABLE_TRACING` | OpenTelemetry tracing | `false` |
| `STORAGE_TYPE` | `local` or `s3` | `local` |

See `backend/.env.example` for complete list.

---

## Database Setup

### PostgreSQL (Recommended)

```bash
# Create database
createdb batchivo

# Run migrations
cd backend
poetry run alembic upgrade head
```

### SQLite (Development Only)

For quick testing, SQLite works out of the box:

```bash
DATABASE_URL=sqlite+aiosqlite:///./batchivo.db
```

---

## TLS/SSL

### With Reverse Proxy (Recommended)

Use Traefik, Caddy, or nginx as a reverse proxy with automatic TLS.

**Caddy example** (`Caddyfile`):

```
batchivo.example.com {
    reverse_proxy frontend:80
}

api.batchivo.example.com {
    reverse_proxy backend:8000
}
```

### With Cloudflare Tunnel

For home lab deployments without port forwarding:

```bash
# Install cloudflared
brew install cloudflared  # or apt install cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create batchivo

# Configure tunnel (config.yml)
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: batchivo.example.com
    service: http://localhost:80
  - service: http_status:404

# Run tunnel
cloudflared tunnel run batchivo
```

---

## Backup & Restore

### Database Backup

```bash
# Backup
docker exec batchivo-postgres pg_dump -U batchivo batchivo > backup.sql

# Or with timestamp
docker exec batchivo-postgres pg_dump -U batchivo batchivo > backup-$(date +%Y%m%d).sql
```

### Database Restore

```bash
# Restore
cat backup.sql | docker exec -i batchivo-postgres psql -U batchivo batchivo
```

### Automated Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * docker exec batchivo-postgres pg_dump -U batchivo batchivo | gzip > /backups/batchivo-$(date +\%Y\%m\%d).sql.gz
```

---

## Kubernetes

For Kubernetes deployments, see `infrastructure/k8s/` for manifests.

```bash
# Apply namespace
kubectl apply -f infrastructure/k8s/namespace.yaml

# Create secrets
kubectl create secret generic backend-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -base64 64) \
  --from-literal=DATABASE_URL=postgresql+psycopg://... \
  -n batchivo

# Apply all manifests
kubectl apply -f infrastructure/k8s/ -n batchivo
```

---

## Monitoring

### Health Checks

- Backend: `GET /health`
- Frontend: `GET /`

### Prometheus Metrics

Backend exposes metrics at `/metrics` when `ENABLE_METRICS=true`.

### Logs

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Specific timeframe
docker-compose logs --since 1h backend
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - DATABASE_URL not set or invalid
# - SECRET_KEY not set
# - Port already in use
```

### Database Connection Failed

```bash
# Test connection
docker exec -it batchivo-postgres psql -U batchivo -c "SELECT 1"

# Check if postgres is ready
docker-compose ps postgres
```

### Migrations Failed

```bash
# Check current migration state
docker exec -it batchivo-backend poetry run alembic current

# Reset if needed (WARNING: destroys data)
docker exec -it batchivo-backend poetry run alembic downgrade base
docker exec -it batchivo-backend poetry run alembic upgrade head
```

---

## Updating

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Run migrations
docker exec -it batchivo-backend poetry run alembic upgrade head
```

---

## Security Recommendations

1. **Change default passwords** - Never use default database credentials
2. **Use TLS** - Always use HTTPS in production
3. **Firewall** - Only expose ports 80/443
4. **Backups** - Test backup restoration regularly
5. **Updates** - Keep images updated for security patches
