---
sidebar_position: 4
---

# Products API

Manage product catalog with bills of materials.

## List Products

```bash
GET /api/v1/products
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Records to skip |
| limit | int | Records per page |
| category | string | Filter by category |
| search | string | Search name/description |

**Response:**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Phone Stand",
      "description": "Universal phone stand with adjustable angle",
      "sku": "PS-001",
      "category": "Desk Accessories",
      "estimated_print_time_minutes": 120,
      "material_cost": 1.50,
      "total_cost": 2.00,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 25,
  "skip": 0,
  "limit": 20
}
```

## Get Product

```bash
GET /api/v1/products/{id}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Phone Stand",
  "description": "Universal phone stand with adjustable angle",
  "sku": "PS-001",
  "category": "Desk Accessories",
  "estimated_print_time_minutes": 120,
  "materials": [
    {
      "id": "...",
      "material_type": "PLA",
      "color": "Black",
      "weight_grams": 45.0,
      "cost": 1.125
    },
    {
      "id": "...",
      "material_type": "PLA",
      "color": "White",
      "weight_grams": 5.0,
      "cost": 0.125
    }
  ],
  "components": [],
  "material_cost": 1.25,
  "component_cost": 0.00,
  "total_cost": 1.25,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-10T15:00:00Z"
}
```

## Create Product

```bash
POST /api/v1/products
Content-Type: application/json

{
  "name": "Phone Stand",
  "description": "Universal phone stand with adjustable angle",
  "sku": "PS-001",
  "category": "Desk Accessories",
  "estimated_print_time_minutes": 120,
  "notes": "Print with 20% infill"
}
```

**Response:** `201 Created`

## Update Product

```bash
PATCH /api/v1/products/{id}
Content-Type: application/json

{
  "description": "Updated description",
  "estimated_print_time_minutes": 90
}
```

## Delete Product

```bash
DELETE /api/v1/products/{id}
```

**Response:** `204 No Content`

## Product Materials

### Add Material to Product

```bash
POST /api/v1/products/{id}/materials
Content-Type: application/json

{
  "material_type": "PLA",
  "color": "Black",
  "weight_grams": 45.0,
  "is_required": true,
  "notes": "Main body"
}
```

### Update Material

```bash
PATCH /api/v1/products/{id}/materials/{material_id}
Content-Type: application/json

{
  "weight_grams": 50.0
}
```

### Remove Material

```bash
DELETE /api/v1/products/{id}/materials/{material_id}
```

## Product Components

For assembled products with sub-components.

### Add Component

```bash
POST /api/v1/products/{id}/components
Content-Type: application/json

{
  "component_product_id": "550e8400-...",
  "quantity": 2,
  "notes": "Include 2 cable clips"
}
```

### Update Component

```bash
PATCH /api/v1/products/{id}/components/{component_id}
Content-Type: application/json

{
  "quantity": 4
}
```

### Remove Component

```bash
DELETE /api/v1/products/{id}/components/{component_id}
```

## Calculate Costs

Recalculate product costs from current material prices:

```bash
POST /api/v1/products/{id}/recalculate
```

**Response:**

```json
{
  "id": "...",
  "material_cost": 1.50,
  "component_cost": 0.50,
  "total_cost": 2.00,
  "cost_breakdown": {
    "materials": [
      {"material": "PLA Black", "weight": 45, "cost": 1.125},
      {"material": "PLA White", "weight": 5, "cost": 0.125}
    ],
    "components": [
      {"component": "M3 Screw Pack", "quantity": 1, "cost": 0.50}
    ]
  }
}
```

## Product Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Product name |
| description | string | No | Full description |
| sku | string | No | Stock keeping unit |
| category | string | No | Product category |
| estimated_print_time_minutes | int | No | Print duration |
| notes | string | No | Print settings, tips |
