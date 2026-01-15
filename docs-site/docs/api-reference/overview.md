---
sidebar_position: 1
---

# API Overview

Batchivo provides a RESTful API for integrating with external tools and automation.

## Base URL

```
Production: https://api.batchivo.example.com/api/v1
Development: http://localhost:8000/api/v1
```

## Interactive Documentation

When running Batchivo, access interactive API docs at:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Spec**: `/openapi.json`

## Authentication

All API requests require authentication via JWT tokens.

```bash
# Get tokens
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Include the access token in requests:

```bash
Authorization: Bearer eyJ...
```

See [Authentication](/docs/api-reference/authentication) for details.

## Response Format

All responses use JSON:

```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

### Error Responses

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid data format |
| 500 | Server Error - Something went wrong |

## Pagination

List endpoints support pagination:

```
GET /api/v1/spools?skip=0&limit=20
```

| Parameter | Default | Max | Description |
|-----------|---------|-----|-------------|
| skip | 0 | - | Records to skip |
| limit | 20 | 100 | Records per page |

## Filtering

Most list endpoints support filtering:

```
GET /api/v1/spools?material_type=PLA&brand=Polymaker
```

## Sorting

Sort by field with direction:

```
GET /api/v1/spools?sort_by=created_at&sort_order=desc
```

## Rate Limiting

API requests are rate-limited:

- 100 requests per minute per user
- 1000 requests per hour per user

Headers indicate limit status:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
```

## Versioning

API version is included in the URL:

```
/api/v1/spools
/api/v2/spools  (future)
```

## Endpoints

| Resource | Endpoint | Description |
|----------|----------|-------------|
| Auth | `/api/v1/auth/*` | Authentication |
| Spools | `/api/v1/spools/*` | Inventory management |
| Products | `/api/v1/products/*` | Product catalog |
| Production Runs | `/api/v1/production-runs/*` | Print tracking |

## SDKs

Official SDKs coming soon:
- Python
- TypeScript/JavaScript

## Webhooks

Webhook support planned for:
- Inventory low stock
- Production run completed
- Order received
