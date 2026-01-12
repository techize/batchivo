# Models API

Manage 3D model catalog with Bill of Materials (BOM), components, and cost calculation. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/models | List all models |
| POST | /api/v1/models | Create a new model |
| GET | /api/v1/models/{id} | Get model details with BOM |
| GET | /api/v1/models/{id}/production-defaults | Get production defaults for model |
| PUT | /api/v1/models/{id} | Update a model |
| DELETE | /api/v1/models/{id} | Delete a model |
| POST | /api/v1/models/import | Import models from CSV |
| GET | /api/v1/models/export | Export models to CSV |

### Model Materials (BOM)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/models/{id}/materials | Add material to BOM |
| DELETE | /api/v1/models/{id}/materials/{mat_id} | Remove material from BOM |

### Model Components
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/models/{id}/components | Add component |
| DELETE | /api/v1/models/{id}/components/{comp_id} | Remove component |

---

## List Models

Retrieve all models with pagination, search, and filtering.

```
GET /api/v1/models
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of items to skip |
| limit | integer | 100 | Max items to return (max: 1000) |
| search | string | - | Search by SKU or name |
| category | string | - | Filter by category |
| is_active | boolean | - | Filter by active status |

**Response: 200 OK**

```json
{
  "total": 45,
  "skip": 0,
  "limit": 100,
  "models": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
      "sku": "MDL-DRAGON-001",
      "name": "Dragon Miniature",
      "description": "Detailed dragon figurine",
      "category": "Miniatures",
      "designer": "Epic Minis",
      "source": "MyMiniFactory",
      "machine": "Bambu Lab X1",
      "print_time_minutes": 180,
      "prints_per_plate": 4,
      "last_printed_date": "2024-03-15",
      "units_in_stock": 10,
      "labor_hours": 0.5,
      "overhead_percentage": 10.0,
      "is_active": true,
      "total_cost": 3.50,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ]
}
```

---

## Create Model

Create a new 3D model entry.

```
POST /api/v1/models
```

**Request Body:**

```json
{
  "sku": "MDL-CASTLE-001",
  "name": "Castle Tower",
  "description": "Modular castle tower piece",
  "category": "Terrain",
  "designer": "OpenForge",
  "source": "Thingiverse",
  "machine": "Bambu Lab X1",
  "print_time_minutes": 240,
  "prints_per_plate": 2,
  "units_in_stock": 0,
  "labor_hours": 0.25,
  "overhead_percentage": 10.0,
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sku | string | Yes | Unique model SKU |
| name | string | Yes | Model name |
| description | string | No | Model description |
| category | string | No | Category name |
| designer | string | No | Designer/creator name |
| source | string | No | Source platform (Thingiverse, etc.) |
| machine | string | No | Preferred printer/machine |
| print_time_minutes | integer | No | Estimated print time |
| prints_per_plate | integer | No | Models per print plate |
| units_in_stock | integer | No | Current stock level |
| labor_hours | decimal | No | Labor time per unit |
| overhead_percentage | decimal | No | Overhead markup % |
| is_active | boolean | No | Default: true |

**Response: 201 Created**

Returns the created model with cost breakdown.

---

## Get Model

Get detailed model information including BOM, components, and cost breakdown.

```
GET /api/v1/models/{model_id}
```

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "sku": "MDL-DRAGON-001",
  "name": "Dragon Miniature",
  "description": "Detailed dragon figurine",
  "category": "Miniatures",
  "designer": "Epic Minis",
  "source": "MyMiniFactory",
  "machine": "Bambu Lab X1",
  "print_time_minutes": 180,
  "prints_per_plate": 4,
  "last_printed_date": "2024-03-15",
  "units_in_stock": 10,
  "labor_hours": 0.5,
  "overhead_percentage": 10.0,
  "is_active": true,
  "materials": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "spool_id": "bbb22222-e89b-12d3-a456-426614174000",
      "weight_grams": 25.5,
      "cost_per_gram": 0.026,
      "spool": {
        "id": "bbb22222-e89b-12d3-a456-426614174000",
        "spool_id": "FIL-001",
        "brand": "Bambu Lab",
        "color": "Matte Black",
        "material_type": {
          "code": "PLA",
          "name": "PLA"
        }
      }
    }
  ],
  "components": [
    {
      "id": "ccc33333-e89b-12d3-a456-426614174000",
      "name": "Base Stand",
      "quantity": 1,
      "cost": 0.50
    }
  ],
  "cost_breakdown": {
    "material_cost": 0.66,
    "component_cost": 0.50,
    "labor_cost": 1.25,
    "overhead_cost": 0.24,
    "total_cost": 2.65
  }
}
```

---

## Get Production Defaults

Get production defaults for a model to auto-populate production run wizard.

```
GET /api/v1/models/{model_id}/production-defaults
```

**Response: 200 OK**

```json
{
  "model_id": "550e8400-e29b-41d4-a716-446655440000",
  "sku": "MDL-DRAGON-001",
  "name": "Dragon Miniature",
  "machine": "Bambu Lab X1",
  "print_time_minutes": 180,
  "prints_per_plate": 4,
  "bom_materials": [
    {
      "spool_id": "bbb22222-e89b-12d3-a456-426614174000",
      "spool_name": "Bambu Lab - PLA - Matte Black",
      "material_type_code": "PLA",
      "color": "Matte Black",
      "color_hex": "#1a1a1a",
      "weight_grams": 25.5,
      "cost_per_gram": 0.026,
      "current_weight": 750.0,
      "is_active": true
    }
  ]
}
```

**Use Case:**
Used by the frontend production run creation wizard to suggest materials based on the model's BOM.

---

## Update Model

Update model properties.

```
PUT /api/v1/models/{model_id}
```

**Request Body:**

```json
{
  "name": "Dragon Miniature - Large",
  "print_time_minutes": 240,
  "units_in_stock": 15
}
```

All fields are optional - only provided fields are updated.

---

## Delete Model

Soft delete a model (sets is_active=false).

```
DELETE /api/v1/models/{model_id}
```

**Response: 204 No Content**

---

## Model Materials (BOM)

Manage the Bill of Materials - which filament spools are needed to print this model.

### Add Material to BOM

```
POST /api/v1/models/{model_id}/materials
```

**Request Body:**

```json
{
  "spool_id": "bbb22222-e89b-12d3-a456-426614174000",
  "weight_grams": 25.5,
  "cost_per_gram": 0.026
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| spool_id | UUID | Yes | Reference to spool |
| weight_grams | decimal | Yes | Filament weight used |
| cost_per_gram | decimal | No | Cost per gram (defaults from spool) |

### Remove Material from BOM

```
DELETE /api/v1/models/{model_id}/materials/{material_id}
```

**Response: 204 No Content**

---

## Model Components

Manage non-filament components (hardware, bases, etc.).

### Add Component

```
POST /api/v1/models/{model_id}/components
```

**Request Body:**

```json
{
  "name": "Magnetic Base",
  "quantity": 1,
  "cost": 0.50
}
```

### Remove Component

```
DELETE /api/v1/models/{model_id}/components/{component_id}
```

**Response: 204 No Content**

---

## CSV Import/Export

### Import Models

Import models from a CSV file.

```
POST /api/v1/models/import
```

**Content-Type:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| file | file | CSV file (.csv) |

**CSV Columns:**
- ID, Name, SKU, Category, Description
- Designer, Source, Machine
- Print Time (13h38m format or minutes)
- Date Printed Last (DD/MM/YYYY)
- Units (stock count)
- Filament1-4, Weight1-4 (multi-material BOM)

**Response: 200 OK**

```json
{
  "success": true,
  "created": 15,
  "updated": 5,
  "skipped": 2,
  "total_rows": 22,
  "errors": [
    "SKU 'MDL-ERR': Invalid material type"
  ]
}
```

### Export Models

Export all models to CSV.

```
GET /api/v1/models/export
```

**Response:** CSV file download

---

## Code Examples

### Python: Create Model with BOM

```python
import httpx

async def create_model_with_bom(token: str, model_data: dict, materials: list):
    async with httpx.AsyncClient() as client:
        # Create model
        response = await client.post(
            "https://api.batchivo.com/api/v1/models",
            json=model_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        model = response.json()

        # Add materials to BOM
        for material in materials:
            await client.post(
                f"https://api.batchivo.com/api/v1/models/{model['id']}/materials",
                json=material,
                headers={"Authorization": f"Bearer {token}"}
            )

        return model
```

### JavaScript: Get Production Defaults

```javascript
async function getProductionDefaults(modelId, token) {
  const response = await fetch(
    `https://api.batchivo.com/api/v1/models/${modelId}/production-defaults`,
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

### cURL: Import Models

```bash
curl -X POST "https://api.batchivo.com/api/v1/models/import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@models.csv"
```
