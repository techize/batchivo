---
sidebar_position: 5
---

# Production Runs API

Track print jobs with material usage and quality metrics.

## List Production Runs

```bash
GET /api/v1/production-runs
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Records to skip |
| limit | int | Records per page |
| status | string | Filter by status |
| printer_name | string | Filter by printer |

**Response:**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "printer_name": "Bambu P1S",
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T14:30:00Z",
      "estimated_print_time_hours": 4.0,
      "actual_print_time_hours": 4.5,
      "estimated_total_filament_grams": 150.0,
      "actual_total_filament_grams": 155.0,
      "quality_rating": 4,
      "created_at": "2024-01-15T09:45:00Z"
    }
  ],
  "total": 100,
  "skip": 0,
  "limit": 20
}
```

## Get Production Run

```bash
GET /api/v1/production-runs/{id}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "printer_name": "Bambu P1S",
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T14:30:00Z",
  "items": [
    {
      "id": "...",
      "product_id": "...",
      "product_name": "Phone Stand",
      "quantity": 3,
      "successful_quantity": 3,
      "failed_quantity": 0,
      "estimated_material_cost": 3.75,
      "estimated_total_cost": 5.25
    }
  ],
  "materials": [
    {
      "id": "...",
      "spool_id": "...",
      "spool_name": "PLA Black (Polymaker)",
      "estimated_weight_grams": 135.0,
      "actual_weight_grams": 140.0,
      "spool_weight_before_grams": 850.0,
      "spool_weight_after_grams": 710.0,
      "estimated_purge_grams": 5.0,
      "actual_purge_grams": 8.0,
      "cost_per_gram": 0.025
    }
  ],
  "quality_rating": 4,
  "quality_notes": "Minor stringing on overhangs",
  "variance_analysis": {
    "material_variance_grams": 5.0,
    "material_variance_percent": 3.3,
    "time_variance_hours": 0.5,
    "time_variance_percent": 12.5
  }
}
```

## Create Production Run

```bash
POST /api/v1/production-runs
Content-Type: application/json

{
  "started_at": "2024-01-15T10:00:00Z",
  "estimated_print_time_hours": 4.0,
  "estimated_total_filament_grams": 150.0,
  "printer_name": "Bambu P1S",
  "status": "in_progress",
  "notes": "Batch print for order #1234"
}
```

**Response:** `201 Created`

## Update Production Run

```bash
PATCH /api/v1/production-runs/{id}
Content-Type: application/json

{
  "status": "completed",
  "quality_rating": 4,
  "quality_notes": "Good quality overall"
}
```

## Delete Production Run

```bash
DELETE /api/v1/production-runs/{id}
```

## Production Run Items

### Add Item

```bash
POST /api/v1/production-runs/{id}/items
Content-Type: application/json

{
  "product_id": "550e8400-...",
  "quantity": 3,
  "estimated_material_cost": 3.75,
  "estimated_total_cost": 5.25
}
```

### Update Item

```bash
PATCH /api/v1/production-runs/{id}/items/{item_id}
Content-Type: application/json

{
  "successful_quantity": 3,
  "failed_quantity": 0
}
```

### Remove Item

```bash
DELETE /api/v1/production-runs/{id}/items/{item_id}
```

## Production Run Materials

### Add Material

```bash
POST /api/v1/production-runs/{id}/materials
Content-Type: application/json

{
  "spool_id": "550e8400-...",
  "estimated_weight_grams": 135.0,
  "estimated_purge_grams": 5.0,
  "cost_per_gram": 0.025
}
```

### Update Material (Record Usage)

```bash
PATCH /api/v1/production-runs/{id}/materials/{material_id}
Content-Type: application/json

{
  "spool_weight_before_grams": 850.0,
  "spool_weight_after_grams": 710.0
}
```

The actual usage is calculated automatically:
```
actual_weight = before - after = 850 - 710 = 140g
```

### Remove Material

```bash
DELETE /api/v1/production-runs/{id}/materials/{material_id}
```

## Complete Production Run

Finalize run and deduct inventory:

```bash
POST /api/v1/production-runs/{id}/complete
```

This endpoint:
1. Validates all materials have actual usage recorded
2. Deducts material from spool inventory
3. Marks run as completed
4. Calculates final duration and variance

**Response:**

```json
{
  "id": "...",
  "status": "completed",
  "completed_at": "2024-01-15T14:30:00Z",
  "inventory_updated": true,
  "spools_updated": [
    {
      "spool_id": "...",
      "previous_weight": 850.0,
      "new_weight": 710.0,
      "deducted": 140.0
    }
  ]
}
```

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Planned, not started |
| `in_progress` | Currently printing |
| `paused` | Temporarily paused |
| `completed` | Successfully finished |
| `failed` | Print failed |
| `cancelled` | Cancelled before completion |

## Quality Ratings

| Rating | Meaning |
|--------|---------|
| 1 | Failed/Unusable |
| 2 | Major defects |
| 3 | Minor defects |
| 4 | Good quality |
| 5 | Perfect |
