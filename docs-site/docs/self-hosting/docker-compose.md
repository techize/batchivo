---
sidebar_position: 2
---

# Docker Compose

The recommended way to self-host Batchivo.

## Quick Start

```bash
# Clone repository
git clone https://github.com/techize/batchivo.git
cd batchivo

# Copy environment files
cp backend/.env.example backend/.env

# Edit backend/.env and set SECRET_KEY:
# python -c "import secrets; print(secrets.token_urlsafe(64))"

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

## Production Configuration

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
    image: ghcr.io/techize/batchivo-backend:latest
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
    image: ghcr.io/techize/batchivo-frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Running Production Stack

```bash
# Set required environment variables
export DB_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Start
docker-compose -f docker-compose.prod.yml up -d
```

## Updating

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Run migrations
docker exec -it batchivo-backend poetry run alembic upgrade head
```

## Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last hour
docker-compose logs --since 1h backend
```

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
