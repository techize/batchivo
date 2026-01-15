---
sidebar_position: 3
---

# Spools API

Manage filament spool inventory.

## List Spools

```bash
GET /api/v1/spools
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Records to skip (default: 0) |
| limit | int | Records per page (default: 20, max: 100) |
| material_type | string | Filter by material (PLA, PETG, etc.) |
| brand | string | Filter by brand |
| color | string | Filter by color |
| in_stock | bool | Filter by availability |

**Example:**

```bash
curl 'http://localhost:8000/api/v1/spools?material_type=PLA&limit=10' \
  -H 'Authorization: Bearer eyJ...'
```

**Response:**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "material_type": "PLA",
      "brand": "Polymaker",
      "color": "Black",
      "color_hex": "#000000",
      "finish": "Matte",
      "diameter_mm": 1.75,
      "net_weight_grams": 1000,
      "remaining_weight_grams": 750,
      "spool_weight_grams": 200,
      "purchase_price": 25.00,
      "cost_per_gram": 0.025,
      "supplier": "Amazon",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 10
}
```

## Get Spool

```bash
GET /api/v1/spools/{id}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "material_type": "PLA",
  "brand": "Polymaker",
  "color": "Black",
  ...
}
```

## Create Spool

```bash
POST /api/v1/spools
Content-Type: application/json

{
  "material_type": "PLA",
  "brand": "Polymaker",
  "color": "Black",
  "color_hex": "#000000",
  "finish": "Matte",
  "diameter_mm": 1.75,
  "net_weight_grams": 1000,
  "spool_weight_grams": 200,
  "purchase_price": 25.00,
  "supplier": "Amazon",
  "purchase_date": "2024-01-01",
  "notes": "Good quality, consistent diameter"
}
```

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "material_type": "PLA",
  ...
}
```

## Update Spool

```bash
PATCH /api/v1/spools/{id}
Content-Type: application/json

{
  "remaining_weight_grams": 500,
  "notes": "Updated after print job"
}
```

**Response:** `200 OK`

## Delete Spool

```bash
DELETE /api/v1/spools/{id}
```

**Response:** `204 No Content`

## Deduct Weight

Deduct material from spool after use:

```bash
POST /api/v1/spools/{id}/deduct
Content-Type: application/json

{
  "weight_grams": 50.5,
  "reason": "Production run #42"
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "remaining_weight_grams": 449.5,
  "deducted": 50.5
}
```

## Spool Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| material_type | string | Yes | PLA, PETG, ABS, etc. |
| brand | string | No | Manufacturer name |
| color | string | Yes | Color name |
| color_hex | string | No | Hex color code |
| finish | string | No | Matte, Glossy, Silk, etc. |
| diameter_mm | float | Yes | 1.75 or 2.85 |
| net_weight_grams | float | Yes | Total filament weight |
| remaining_weight_grams | float | No | Current weight (defaults to net) |
| spool_weight_grams | float | No | Empty spool weight |
| purchase_price | float | No | Cost per spool |
| supplier | string | No | Where purchased |
| purchase_date | date | No | When purchased |
| notes | string | No | Additional notes |

## Material Types

Supported values for `material_type`:

- `PLA`
- `PETG`
- `ABS`
- `TPU`
- `ASA`
- `Nylon`
- `PC`
- `HIPS`
- `PVA`
- `Custom`
