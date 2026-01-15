---
sidebar_position: 2
---

# Architecture

Technical overview of Batchivo's architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│              (Web Browser, Mobile, API Consumers)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Reverse Proxy                             │
│                 (Traefik / Caddy / nginx)                    │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
┌─────────────▼─────────────┐   ┌────────────▼────────────────┐
│       Frontend            │   │         Backend              │
│    (React + Vite)         │   │        (FastAPI)             │
│                           │   │                              │
│  • Single Page App        │   │  • REST API                  │
│  • TypeScript             │   │  • JWT Auth                  │
│  • TailwindCSS            │   │  • Async SQLAlchemy          │
│  • shadcn/ui components   │   │  • Alembic migrations        │
└───────────────────────────┘   └──────────────┬──────────────┘
                                               │
              ┌────────────────────────────────┼────────────────┐
              │                                │                │
    ┌─────────▼─────────┐         ┌───────────▼──────┐   ┌─────▼─────┐
    │    PostgreSQL     │         │      Redis       │   │  Storage  │
    │                   │         │                  │   │           │
    │  • Multi-tenant   │         │  • Session cache │   │  • Local  │
    │  • RLS policies   │         │  • Rate limiting │   │  • S3     │
    │  • Full-text      │         │  • Job queue     │   │           │
    └───────────────────┘         └──────────────────┘   └───────────┘
```

## Backend Stack

### FastAPI

- Async request handling
- Automatic OpenAPI documentation
- Pydantic validation
- Dependency injection

### SQLAlchemy 2.0

- Async engine and sessions
- Declarative models
- Relationship management

### Alembic

- Database migrations
- Version tracking
- Auto-generation support

### Authentication

- JWT tokens (access + refresh)
- Secure password hashing (bcrypt)
- Token rotation

## Frontend Stack

### React 18

- Function components
- Hooks for state management
- React Router for navigation

### TypeScript

- Strict type checking
- Interfaces for API responses
- Generic components

### UI Framework

- TailwindCSS for styling
- shadcn/ui components
- Responsive design

### Build Tool

- Vite for fast development
- Hot module replacement
- Optimized production builds

## Database Design

### Multi-Tenancy

Row-Level Security (RLS) ensures data isolation:

```sql
CREATE POLICY tenant_isolation ON spools
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### Core Tables

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│    tenants    │────<│     users     │     │    spools     │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                    │
┌───────────────┐     ┌───────────────┐            │
│   products    │────<│product_materials│          │
└───────┬───────┘     └───────────────┘            │
        │                                          │
┌───────▼───────────────────────────────────────────────────┐
│                    production_runs                         │
├───────────────────┬───────────────────────────────────────┤
│ production_run_   │         production_run_               │
│      items        │            materials                  │
└───────────────────┴───────────────────────────────────────┘
```

## API Design

### RESTful Principles

- Resource-based URLs
- HTTP methods for actions
- Consistent response format

### Versioning

```
/api/v1/spools
/api/v2/spools  (future breaking changes)
```

### Error Handling

```json
{
  "detail": "Spool not found",
  "code": "NOT_FOUND",
  "status_code": 404
}
```

## Security

### Authentication Flow

```
1. User submits credentials
2. Server validates and issues JWT pair
3. Client stores tokens securely
4. Access token included in requests
5. Refresh token used when access expires
```

### Data Protection

- Passwords hashed with bcrypt
- Sensitive data encrypted at rest
- HTTPS enforced in production
- CORS configured per environment

## Observability

### Tracing (OpenTelemetry)

- Distributed request tracing
- Span collection
- Jaeger/Tempo integration

### Metrics (Prometheus)

- Request latency
- Error rates
- Database pool stats

### Logging (Structured)

- JSON format
- Request context
- Loki integration

## Deployment

### Container Images

- Multi-stage Docker builds
- Non-root user
- Health checks

### Orchestration

- Docker Compose for simple deployments
- Kubernetes for production scale
- Helm charts available

### CI/CD

- GitHub Actions
- Automated testing
- Image building and pushing
