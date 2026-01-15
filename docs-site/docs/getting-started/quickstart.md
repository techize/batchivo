---
sidebar_position: 1
---

# Quick Start

Get Batchivo running in under 5 minutes using Docker Compose.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

## Installation

```bash
# Clone repository
git clone https://github.com/techize/batchivo.git
cd batchivo

# Copy environment files
cp backend/.env.example backend/.env

# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Copy output to SECRET_KEY in backend/.env

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

## Verify Installation

1. **Backend API**: Open http://localhost:8000/docs to see the interactive API documentation
2. **Frontend**: Open http://localhost:5173 to access the web interface
3. **Health Check**: `curl http://localhost:8000/health`

## Next Steps

- [Configure environment variables](/docs/self-hosting/environment-variables)
- [Set up TLS/SSL](/docs/self-hosting/overview#tlsssl)
- [Create your first spool](/docs/guides/inventory-management)

## Development Setup

For contributing or local development, see the [full installation guide](/docs/getting-started/installation) for setting up without Docker.
