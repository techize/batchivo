# API Quickstart

Get started with the Batchivo API in 5 minutes.

---

## Prerequisites

- Running Batchivo instance (local or hosted)
- `curl` or similar HTTP client
- A registered user account

---

## 1. Get an Access Token

First, authenticate to get a JWT token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-password"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

Save the `access_token` for subsequent requests:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

---

## 2. List Your Spools

Get all filament spools in your inventory:

```bash
curl -X GET "http://localhost:8000/api/v1/spools" \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "total": 12,
  "page": 1,
  "page_size": 20,
  "spools": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Prusament Galaxy Black",
      "material_type": "PLA",
      "color": "Galaxy Black",
      "brand": "Prusament",
      "weight_initial_g": 1000,
      "weight_current_g": 750,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## 3. Create a Spool

Add a new spool to inventory:

```bash
curl -X POST "http://localhost:8000/api/v1/spools" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "eSun PLA+ White",
    "material_type": "PLA+",
    "color": "White",
    "brand": "eSun",
    "weight_initial_g": 1000,
    "weight_current_g": 1000,
    "price_paid": 19.99,
    "supplier": "Amazon"
  }'
```

Response:

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "eSun PLA+ White",
  "material_type": "PLA+",
  ...
}
```

---

## 4. List Products

Get your product catalog:

```bash
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. Get Product with Costs

Retrieve a product with full cost breakdown:

```bash
curl -X GET "http://localhost:8000/api/v1/products/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

Response includes calculated costs:

```json
{
  "id": "...",
  "name": "Dragon Miniature",
  "sku": "DRAG-001",
  "costs": {
    "material_cost": 2.50,
    "component_cost": 0.75,
    "labor_cost": 5.00,
    "overhead_cost": 1.00,
    "total_cost": 9.25
  }
}
```

---

## Common Patterns

### Filtering

Most list endpoints support filtering:

```bash
# Spools by material type
curl "http://localhost:8000/api/v1/spools?material_type=PLA" \
  -H "Authorization: Bearer $TOKEN"

# Products by category
curl "http://localhost:8000/api/v1/products?category_id=..." \
  -H "Authorization: Bearer $TOKEN"
```

### Pagination

Control page size and navigate results:

```bash
curl "http://localhost:8000/api/v1/spools?page=2&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Sorting

Sort by field (prefix with `-` for descending):

```bash
# Newest first
curl "http://localhost:8000/api/v1/spools?sort=-created_at" \
  -H "Authorization: Bearer $TOKEN"

# By weight (ascending)
curl "http://localhost:8000/api/v1/spools?sort=weight_current_g" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Error Handling

The API returns consistent error responses:

```json
{
  "detail": "Spool not found",
  "status_code": 404
}
```

Common status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (no permission) |
| 404 | Not found |
| 422 | Validation error |
| 429 | Rate limited |

---

## Refresh Token

When your access token expires, use the refresh token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token"
  }'
```

---

## Interactive Docs

For interactive API exploration, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide live testing and full schema documentation.

---

## Next Steps

- [Authentication](./authentication.md) - Full auth flow details
- [Spools API](./spools.md) - Complete spool endpoints
- [Products API](./products.md) - Product management
- [Production Runs](./production-runs.md) - Manufacturing tracking
