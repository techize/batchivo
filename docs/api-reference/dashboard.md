# Dashboard API

Business intelligence endpoints for the authenticated home page. Provides real-time statistics, active production tracking, and performance analytics. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/dashboard/summary | Get dashboard statistics |
| GET | /api/v1/dashboard/active-production | Get active production runs |
| GET | /api/v1/dashboard/low-stock | Get low stock spool alerts |
| GET | /api/v1/dashboard/recent-activity | Get recent activity feed |
| GET | /api/v1/dashboard/performance-charts | Get performance chart data |
| GET | /api/v1/dashboard/failure-analytics | Get failure analytics |

---

## Dashboard Summary

Get high-level statistics for the dashboard overview.

```
GET /api/v1/dashboard/summary
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| low_stock_threshold | integer | 10 | Low stock threshold percentage (1-100) |

**Response: 200 OK**

```json
{
  "active_prints": 3,
  "completed_today": 8,
  "failed_today": 1,
  "cancelled_today": 0,
  "low_stock_count": 5,
  "success_rate_7d": 94.5,
  "total_waste_7d_grams": 125.5
}
```

| Field | Description |
|-------|-------------|
| active_prints | Count of in_progress production runs |
| completed_today | Runs completed today |
| failed_today | Runs failed today |
| cancelled_today | Runs cancelled today |
| low_stock_count | Spools below threshold percentage |
| success_rate_7d | 7-day success rate (0-100) |
| total_waste_7d_grams | Total waste in last 7 days (grams) |

---

## Active Production

Get currently active production runs for quick overview.

```
GET /api/v1/dashboard/active-production
```

**Response: 200 OK**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "run_number": "20240315-001",
    "started_at": "2024-03-15T08:00:00Z",
    "printer_name": "Bambu Lab X1",
    "estimated_print_time_hours": 6.5,
    "items_count": 3,
    "total_quantity": 12,
    "products_summary": "Dragon Miniature x4, Tower Base x4, Shield x4"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "run_number": "20240315-002",
    "started_at": "2024-03-15T10:30:00Z",
    "printer_name": "Bambu Lab P1S",
    "estimated_print_time_hours": 4.0,
    "items_count": 5,
    "total_quantity": 20,
    "products_summary": "Dice Tower x5, Coin Holder x5, Token Set x5 +2 more"
  }
]
```

---

## Low Stock Alerts

Get spools below stock threshold, sorted by most critical first.

```
GET /api/v1/dashboard/low-stock
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| threshold_percent | integer | 10 | Stock threshold percentage (1-100) |
| limit | integer | 20 | Maximum spools to return (max: 100) |

**Response: 200 OK**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "spool_id": "FIL-001",
    "brand": "Bambu Lab",
    "color": "Matte Black",
    "color_hex": "#1a1a1a",
    "material_type": "PLA",
    "current_weight": 45.0,
    "initial_weight": 1000.0,
    "percent_remaining": 4.5,
    "is_critical": true
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "spool_id": "FIL-015",
    "brand": "Polymaker",
    "color": "Galaxy Black",
    "color_hex": "#2a2a2a",
    "material_type": "PETG",
    "current_weight": 85.0,
    "initial_weight": 1000.0,
    "percent_remaining": 8.5,
    "is_critical": false
  }
]
```

| Field | Description |
|-------|-------------|
| is_critical | True if below 5% remaining |

---

## Recent Activity

Get recent inventory transactions for activity feed.

```
GET /api/v1/dashboard/recent-activity
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 20 | Maximum items to return (max: 100) |

**Response: 200 OK**

```json
[
  {
    "id": "aaa11111-e89b-12d3-a456-426614174000",
    "transaction_type": "production",
    "created_at": "2024-03-15T14:30:00Z",
    "spool_id": "FIL-001",
    "spool_color": "Matte Black",
    "weight_change": -45.5,
    "description": "Production run completion",
    "production_run_id": "550e8400-e29b-41d4-a716-446655440000",
    "run_number": "20240315-001"
  },
  {
    "id": "bbb22222-e89b-12d3-a456-426614174000",
    "transaction_type": "waste",
    "created_at": "2024-03-15T12:00:00Z",
    "spool_id": "FIL-003",
    "spool_color": "Jade White",
    "weight_change": -25.0,
    "description": "Failed print - layer adhesion",
    "production_run_id": null,
    "run_number": null
  }
]
```

**Transaction Types:**
- `production` - Normal production usage
- `waste` - Failed print waste
- `adjustment` - Manual stock adjustment
- `purchase` - Stock added from purchase

---

## Performance Charts

Get data for dashboard performance visualizations.

```
GET /api/v1/dashboard/performance-charts
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 7 | Number of days to include (1-90) |

**Response: 200 OK**

```json
{
  "success_rate_trend": [
    {
      "date": "2024-03-09",
      "success_rate": 100.0,
      "completed": 5,
      "failed": 0
    },
    {
      "date": "2024-03-10",
      "success_rate": 87.5,
      "completed": 7,
      "failed": 1
    }
  ],
  "material_usage": [
    {
      "material_type": "Matte Black",
      "total_grams": 450.5,
      "color": "Matte Black"
    },
    {
      "material_type": "Jade White",
      "total_grams": 320.0,
      "color": "Jade White"
    }
  ],
  "daily_production": [
    {
      "date": "2024-03-09",
      "items_completed": 24,
      "items_failed": 0,
      "runs_completed": 5
    },
    {
      "date": "2024-03-10",
      "items_completed": 32,
      "items_failed": 4,
      "runs_completed": 8
    }
  ]
}
```

---

## Failure Analytics

Get detailed failure analysis data.

```
GET /api/v1/dashboard/failure-analytics
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 30 | Number of days to analyze (1-90) |

**Response: 200 OK**

```json
{
  "failure_by_reason": [
    {
      "reason": "layer_adhesion",
      "count": 5,
      "percentage": 35.7
    },
    {
      "reason": "bed_adhesion",
      "count": 4,
      "percentage": 28.6
    },
    {
      "reason": "stringing",
      "count": 3,
      "percentage": 21.4
    }
  ],
  "most_common_failures": [
    {
      "reason": "layer_adhesion",
      "count": 5,
      "percentage": 35.7
    }
  ],
  "failure_trends": [
    {
      "date": "2024-03-14",
      "count": 2,
      "reasons": {
        "layer_adhesion": 1,
        "bed_adhesion": 1
      }
    },
    {
      "date": "2024-03-15",
      "count": 1,
      "reasons": {
        "stringing": 1
      }
    }
  ],
  "total_failures": 14,
  "failure_rate": 8.5
}
```

---

## Code Examples

### Python: Get Dashboard Data

```python
import httpx

async def get_dashboard_data(token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch all dashboard data in parallel
        summary, active, low_stock = await asyncio.gather(
            client.get("https://api.nozzly.app/api/v1/dashboard/summary", headers=headers),
            client.get("https://api.nozzly.app/api/v1/dashboard/active-production", headers=headers),
            client.get("https://api.nozzly.app/api/v1/dashboard/low-stock", headers=headers)
        )

        return {
            "summary": summary.json(),
            "active_production": active.json(),
            "low_stock_alerts": low_stock.json()
        }
```

### JavaScript: Refresh Dashboard

```javascript
async function refreshDashboard(token) {
  const [summary, charts, failures] = await Promise.all([
    fetch("https://api.nozzly.app/api/v1/dashboard/summary", {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()),

    fetch("https://api.nozzly.app/api/v1/dashboard/performance-charts?days=7", {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()),

    fetch("https://api.nozzly.app/api/v1/dashboard/failure-analytics?days=30", {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json())
  ]);

  return { summary, charts, failures };
}
```

---

## Dashboard Widgets

### Summary Cards
Use `/summary` for top-level stats cards:
- Active prints count
- Today's completions/failures
- Low stock alerts count
- 7-day success rate

### Active Production Table
Use `/active-production` for live production overview with:
- Run number and start time
- Printer assignment
- Products being printed
- Estimated completion

### Low Stock Alerts
Use `/low-stock` for inventory warnings:
- Sort by criticality (lowest first)
- Highlight critical (<5%) in red
- Link to spool details for reordering

### Performance Charts
Use `/performance-charts` for visualizations:
- Line chart: Success rate trend
- Pie/bar chart: Material usage by color
- Bar chart: Daily production volume

### Failure Analysis
Use `/failure-analytics` for quality insights:
- Pie chart: Failures by reason
- Trend line: Failure rate over time
- Action items: Most common failure types
