# Analytics API

Business intelligence and variance analysis for production optimization. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/analytics/variance-report | Get filament usage variance analysis |
| GET | /api/v1/analytics/products/{id}/production-history | Get product production history |
| GET | /api/v1/analytics/spools/{id}/production-usage | Get spool usage history |

---

## Variance Report

Analyze filament usage variance across production runs to identify estimation accuracy issues.

```
GET /api/v1/analytics/variance-report
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 30 | Number of days to analyze (1-365) |
| product_id | UUID | - | Filter by specific product |
| variance_threshold | float | - | Only include runs with variance above this % |

**Response: 200 OK**

```json
{
  "by_product": [
    {
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "product_name": "Dragon Miniature",
      "sku": "DRAGON-001",
      "run_count": 15,
      "avg_variance_percent": 8.5,
      "total_estimated_grams": 2250.0,
      "total_actual_grams": 2441.3,
      "min_variance_percent": -2.1,
      "max_variance_percent": 18.5
    }
  ],
  "highest_variance_runs": [
    {
      "run_id": "111e2222-e89b-12d3-a456-426614174000",
      "run_number": "20240315-001",
      "completed_at": "2024-03-15T14:30:00Z",
      "estimated_grams": 150.0,
      "actual_grams": 177.8,
      "variance_grams": 27.8,
      "variance_percent": 18.5
    }
  ],
  "variance_trends": [
    {
      "date": "2024-03-15",
      "avg_variance_percent": 5.2,
      "run_count": 3
    },
    {
      "date": "2024-03-14",
      "avg_variance_percent": 8.1,
      "run_count": 5
    }
  ],
  "summary": {
    "total_runs_analyzed": 42,
    "avg_variance_percent": 6.8,
    "runs_over_estimate": 28,
    "runs_under_estimate": 14,
    "runs_above_10_percent": 8
  }
}
```

**Use Cases:**
- Identify products that consistently over/under-estimate filament usage
- Find problematic production runs for investigation
- Track variance trends over time to improve estimations

---

## Product Production History

Get complete production history for a specific product.

```
GET /api/v1/analytics/products/{product_id}/production-history
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 90 | Number of days to include (1-365) |
| status_filter | string | - | Filter by run status |
| skip | integer | 0 | Pagination offset |
| limit | integer | 50 | Max results (max: 200) |

**Response: 200 OK**

```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_name": "Dragon Miniature",
  "total_runs": 25,
  "total_produced": 112,
  "total_failed": 8,
  "overall_success_rate": 93.3,
  "avg_estimated_cost": 4.50,
  "avg_actual_cost": 4.88,
  "production_history": [
    {
      "run_id": "111e2222-e89b-12d3-a456-426614174000",
      "run_number": "20240315-001",
      "started_at": "2024-03-15T08:00:00Z",
      "completed_at": "2024-03-15T14:30:00Z",
      "status": "completed",
      "quantity_planned": 5,
      "quantity_successful": 5,
      "quantity_failed": 0,
      "success_rate": 100.0,
      "estimated_cost": 4.50,
      "actual_cost": 4.72,
      "variance_percent": 4.9
    }
  ]
}
```

**Metrics Included:**
- `quantity_planned` - How many were intended
- `quantity_successful` - How many printed successfully
- `quantity_failed` - How many failed
- `success_rate` - Percentage of successful prints
- `estimated_cost` - Predicted material cost
- `actual_cost` - Real material cost (completed runs only)
- `variance_percent` - Cost variance percentage

---

## Spool Production Usage

Get usage history for a specific spool across all production runs.

```
GET /api/v1/analytics/spools/{spool_id}/production-usage
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 90 | Number of days to include (1-365) |
| skip | integer | 0 | Pagination offset |
| limit | integer | 50 | Max results (max: 200) |

**Response: 200 OK**

```json
{
  "spool_id": "222e3333-e89b-12d3-a456-426614174000",
  "spool_code": "FIL-001",
  "color": "Matte Black",
  "material_type": "PLA",
  "total_usage_grams": 850.5,
  "avg_usage_per_run": 42.5,
  "run_count": 20,
  "usage_history": [
    {
      "run_id": "111e2222-e89b-12d3-a456-426614174000",
      "run_number": "20240315-001",
      "date": "2024-03-15T08:00:00Z",
      "estimated_weight": 40.0,
      "actual_weight": 43.2,
      "variance_grams": 3.2,
      "variance_percent": 8.0,
      "products_printed": ["Dragon Miniature", "Tower Base"]
    }
  ]
}
```

**Tracking Details:**
- Shows every production run that used this spool
- Tracks estimated vs actual usage with variance
- Lists what products were printed in each run
- Helps identify usage patterns and spool consumption rate

---

## Code Examples

### Python: Get Variance Report

```python
import httpx

async def get_variance_report(token: str, days: int = 30, threshold: float = None):
    params = {"days": days}
    if threshold:
        params["variance_threshold"] = threshold

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.batchivo.com/api/v1/analytics/variance-report",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Get Product History

```javascript
async function getProductHistory(productId, days = 90, token) {
  const response = await fetch(
    `https://api.batchivo.com/api/v1/analytics/products/${productId}/production-history?days=${days}`,
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

### cURL: Get Spool Usage

```bash
curl -X GET "https://api.batchivo.com/api/v1/analytics/spools/SPOOL_ID/production-usage?days=60" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Analysis Tips

### Reducing Variance

High variance indicates estimation problems. Common causes:
- **Positive variance (using more):** Purge/tower estimates too low, stringing/supports not accounted
- **Negative variance (using less):** Overly cautious estimates, hollow infill patterns

### Using the Trend Data

The `variance_trends` array shows daily averages. Look for:
- Consistent direction (always over or under)
- Sudden changes (new filament brand, printer issues)
- Gradual improvement (better estimates over time)

### Product-Level Analysis

Use `by_product` to identify which products need estimate adjustments:
- High `avg_variance_percent` = systematic estimation error
- Large `min_variance_percent` to `max_variance_percent` gap = inconsistent printing
