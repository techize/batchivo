---
sidebar_position: 4
---

# Environment Variables

Complete reference for Batchivo configuration.

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ chars) | `openssl rand -base64 64` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://user:pass@host:5432/db` |

## Optional Variables

### Application

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Database

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection | Required |
| `DATABASE_POOL_SIZE` | Connection pool size | `5` |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `10` |

### Redis (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |

### CORS

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["http://localhost:5173"]` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials | `true` |

### Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |

### Observability

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` |
| `ENABLE_METRICS` | Enable Prometheus metrics | `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | - |

### Storage

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_TYPE` | Storage backend (`local` or `s3`) | `local` |
| `STORAGE_PATH` | Local storage path | `./uploads` |
| `S3_BUCKET` | S3 bucket name | - |
| `S3_REGION` | S3 region | - |

## Generating Secret Key

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(64))"

# OpenSSL
openssl rand -base64 64
```

## Example .env File

```bash
# Required
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=postgresql+psycopg://batchivo:password@localhost:5432/batchivo

# Optional
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=["https://batchivo.example.com"]

# Redis (if using)
REDIS_URL=redis://localhost:6379/0

# Observability (if using)
ENABLE_TRACING=true
ENABLE_METRICS=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Docker Compose Environment

Set variables in your shell before running docker-compose:

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
export DB_PASSWORD=$(openssl rand -base64 32)

docker-compose up -d
```

Or use a `.env` file in the same directory as `docker-compose.yml`:

```bash
SECRET_KEY=your-key
DB_PASSWORD=your-password
```
