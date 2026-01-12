# Batchivo API Reference

## Overview

The Batchivo API provides programmatic access to your 3D print business management platform. This RESTful API supports inventory management, production tracking, order processing, and analytics.

## Base URL

```
Production: https://api.batchivo.com/api/v1
Development: http://localhost:8000/api/v1
```

## API Versioning

The API uses URL-based versioning. The current version is `v1`. All endpoints are prefixed with `/api/v1`.

Future versions will be released as `/api/v2`, etc., with backwards compatibility maintained for major versions.

## Authentication

All API requests (except public endpoints) require authentication using JWT bearer tokens.

```bash
curl -X GET "https://api.batchivo.com/api/v1/spools" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

See [Authentication](./authentication.md) for complete OAuth flow and token management.

### Token Types

| Token Type | Expiration | Purpose |
|------------|------------|---------|
| Access Token | 24 hours | API request authentication |
| Refresh Token | 7 days | Obtain new access tokens |

## Rate Limiting

The API implements rate limiting to ensure fair usage:

| Endpoint Type | Rate Limit |
|---------------|------------|
| Authentication (login, register) | 5 requests/minute |
| Password Reset | 3 requests/minute |
| General API | 100 requests/minute |

Rate limits are applied per IP address. When exceeded, the API returns HTTP 429 with a `Retry-After` header.

```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```

## Pagination

List endpoints support pagination using offset/limit:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | Items per page (max: 100) |

### Response Format

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "spools": [...]
}
```

## Error Handling

The API uses standard HTTP status codes and returns errors in a consistent format:

### Error Response Schema

```json
{
  "detail": "Human-readable error message"
}
```

### Validation Error Schema

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Validation error message",
      "type": "error_type"
    }
  ]
}
```

### Common Status Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Validation Error - Invalid request body |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Server Error |

## Multi-Tenancy

Batchivo is a multi-tenant platform. Each user belongs to one or more tenants (workspaces). The tenant context is derived from the JWT token.

All resources are scoped to the current tenant - you can only access resources belonging to your tenant.

## API Categories

### Core Resources

| Category | Description | Documentation |
|----------|-------------|---------------|
| Authentication | User login, registration, password reset | [authentication.md](./authentication.md) |
| Spools | Filament inventory management | [spools.md](./spools.md) |
| Products | Product catalog management | [products.md](./products.md) |
| Models | 3D model library with BOM | [models.md](./models.md) |
| Production Runs | Print job tracking with plates | [production-runs.md](./production-runs.md) |
| Orders | Order processing and fulfillment | [orders.md](./orders.md) |
| Printers | 3D printer management | [printers.md](./printers.md) |
| Categories | Product categorization | [categories.md](./categories.md) |
| Designers | Designer/creator profiles | [designers.md](./designers.md) |
| Consumables | Non-filament inventory | [consumables.md](./consumables.md) |

### Sales & Commerce

| Category | Description | Documentation |
|----------|-------------|---------------|
| Sales Channels | Multi-platform selling | [sales-channels.md](./sales-channels.md) |
| Shipping | UK postcode validation and rates | [shipping.md](./shipping.md) |

### Analytics & Monitoring

| Category | Description | Documentation |
|----------|-------------|---------------|
| Dashboard | Business intelligence metrics | [dashboard.md](./dashboard.md) |
| Analytics | Variance analysis and trends | [analytics.md](./analytics.md) |

### Configuration & Integration

| Category | Description | Documentation |
|----------|-------------|---------------|
| Settings | Tenant and payment configuration | [settings.md](./settings.md) |
| Webhooks | Event notifications | [webhooks.md](./webhooks.md) |

## Request Examples

### cURL

```bash
curl -X GET "https://api.batchivo.com/api/v1/spools?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Python (httpx)

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.batchivo.com/api/v1/spools",
        params={"page": 1, "page_size": 10},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    spools = response.json()
```

### JavaScript (fetch)

```javascript
const response = await fetch(
  "https://api.batchivo.com/api/v1/spools?page=1&page_size=10",
  {
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json"
    }
  }
);
const data = await response.json();
```

## OpenAPI / Swagger

Interactive API documentation is available in development environments:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Production environments have these disabled for security.

## Postman Collection

Import the [Batchivo API Postman Collection](./batchivo-api.postman_collection.json) for easy testing.

## Support

For API support, please contact:
- Email: api-support@batchivo.com
- Documentation Issues: [GitHub Issues](https://github.com/batchivo/docs/issues)
