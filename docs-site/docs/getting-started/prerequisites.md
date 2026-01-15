---
sidebar_position: 2
---

# Prerequisites

## Docker Deployment (Recommended)

For the quickest setup, you only need:

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| RAM | 2GB+ | Minimum for all services |
| Disk | 10GB+ | For images and data |

## Development Setup

For local development without Docker:

### Backend

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | Runtime |
| Poetry | Latest | Dependency management |
| PostgreSQL | 16+ | Production database |
| SQLite | - | Development database (optional) |

### Frontend

| Requirement | Version | Notes |
|-------------|---------|-------|
| Node.js | 20+ | Runtime |
| npm | 10+ | Package manager |

## Optional Components

| Component | Purpose |
|-----------|---------|
| Redis | Caching and session storage |
| Cloudflare Tunnel | Secure external access |
| Prometheus/Grafana | Monitoring and metrics |

## Checking Versions

```bash
# Docker
docker --version
docker compose version

# Python
python3 --version
poetry --version

# Node.js
node --version
npm --version
```
