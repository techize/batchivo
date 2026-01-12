# Spools API

Manage filament spool inventory. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/spools | List all spools |
| POST | /api/v1/spools | Create a new spool |
| GET | /api/v1/spools/{spool_id} | Get spool details |
| PUT | /api/v1/spools/{spool_id} | Update a spool |
| DELETE | /api/v1/spools/{spool_id} | Delete a spool |
| POST | /api/v1/spools/{spool_id}/duplicate | Duplicate a spool |
| GET | /api/v1/spools/export | Export spools |
| POST | /api/v1/spools/import | Import spools |
| GET | /api/v1/spools/material-types | List material types |
| POST | /api/v1/spools/material-types | Create material type |

---

## List Spools

Retrieve all spools with pagination, search, and filtering.

```
GET /api/v1/spools
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| page_size | integer | 20 | Items per page (max: 100) |
| search | string | - | Search by spool_id, brand, or color |
| material_type_id | UUID | - | Filter by material type |
| is_active | boolean | - | Filter by active status |
| low_stock_only | boolean | false | Show only spools with <20% remaining |

**Response: 200 OK**

```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "spools": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "spool_id": "FIL-001",
      "material_type_id": "123e4567-e89b-12d3-a456-426614174000",
      "material_type_code": "PLA",
      "material_type_name": "PLA (Polylactic Acid)",
      "brand": "Bambu Lab",
      "color": "Matte Black",
      "finish": "matte",
      "diameter_mm": 1.75,
      "initial_weight_g": 1000,
      "current_weight_g": 750,
      "empty_spool_weight_g": 200,
      "remaining_weight": 550,
      "remaining_percentage": 73.33,
      "cost_per_kg": 25.99,
      "purchase_date": "2024-01-15",
      "supplier": "Amazon",
      "location": "Shelf A-3",
      "notes": "Great for minis",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ]
}
```

**Example: Search with filters**

```bash
curl -X GET "https://api.batchivo.app/api/v1/spools?search=black&is_active=true&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Create Spool

Create a new filament spool.

```
POST /api/v1/spools
```

**Request Body:**

```json
{
  "spool_id": "FIL-042",
  "material_type_id": "123e4567-e89b-12d3-a456-426614174000",
  "brand": "Bambu Lab",
  "color": "Jade White",
  "finish": "matte",
  "diameter_mm": 1.75,
  "initial_weight_g": 1000,
  "current_weight_g": 1000,
  "empty_spool_weight_g": 200,
  "cost_per_kg": 25.99,
  "purchase_date": "2024-03-15",
  "supplier": "Amazon",
  "location": "Shelf B-2",
  "notes": "Standard PLA spool",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| spool_id | string | No | Auto-generated if not provided |
| material_type_id | UUID | Yes | Material type reference |
| brand | string | Yes | Filament brand |
| color | string | Yes | Color name |
| finish | string | No | "matte", "glossy", "silk", etc. |
| diameter_mm | decimal | Yes | Usually 1.75 or 2.85 |
| initial_weight_g | decimal | Yes | Total filament weight |
| current_weight_g | decimal | Yes | Current remaining weight |
| empty_spool_weight_g | decimal | No | Weight of empty spool |
| cost_per_kg | decimal | No | Purchase price per kg |
| purchase_date | date | No | When purchased |
| supplier | string | No | Where purchased |
| location | string | No | Storage location |
| notes | string | No | Additional notes |
| is_active | boolean | No | Default: true |

**Response: 201 Created**

Returns the created spool object.

---

## Get Spool

Retrieve a specific spool by ID.

```
GET /api/v1/spools/{spool_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| spool_id | UUID | Spool ID |

**Response: 200 OK**

Returns the spool object.

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Spool not found |

---

## Update Spool

Update spool properties. All fields are optional - only provided fields are updated.

```
PUT /api/v1/spools/{spool_id}
```

**Request Body:**

```json
{
  "current_weight_g": 650,
  "location": "Printer 1",
  "notes": "Currently in use"
}
```

**Response: 200 OK**

Returns the updated spool object.

---

## Delete Spool

Permanently delete a spool.

```
DELETE /api/v1/spools/{spool_id}
```

**Response: 204 No Content**

No response body.

---

## Duplicate Spool

Create a copy of an existing spool with a new ID and reset to full weight.

```
POST /api/v1/spools/{spool_id}/duplicate
```

**Response: 201 Created**

Returns the new spool with:
- New auto-generated spool_id
- current_weight_g reset to initial_weight_g
- is_active set to true
- All other properties copied from source

---

## Export Spools

Export all spools in CSV, JSON, or YAML format.

```
GET /api/v1/spools/export?format=csv
```

**Query Parameters:**

| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| format | string | csv | csv, json, yaml |

**Response: 200 OK**

Returns a file download with appropriate content type:
- CSV: `text/csv`
- JSON: `application/json`
- YAML: `application/x-yaml`

**Example:**

```bash
curl -X GET "https://api.batchivo.app/api/v1/spools/export?format=json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o spools.json
```

---

## Import Spools

Import spools from CSV, JSON, or YAML file.

```
POST /api/v1/spools/import
```

**Request:** multipart/form-data

| Field | Type | Description |
|-------|------|-------------|
| file | file | .csv, .json, or .yaml/.yml file |

**Response: 200 OK**

```json
{
  "imported": 15,
  "errors": [
    {
      "row": 3,
      "spool_id": "FIL-ERR",
      "error": "Invalid material_type_id"
    }
  ],
  "total": 16
}
```

---

## Material Types

### List Material Types

Retrieve all available material types (global, not tenant-scoped).

```
GET /api/v1/spools/material-types
```

**Response: 200 OK**

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "code": "PLA",
    "name": "PLA (Polylactic Acid)",
    "description": "Easy to print, biodegradable plastic",
    "typical_density": 1.24,
    "typical_cost_per_kg": 20.00,
    "min_temp": 190,
    "max_temp": 220,
    "bed_temp": 60,
    "is_active": true
  },
  {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "code": "PETG",
    "name": "PETG (Polyethylene Terephthalate Glycol)",
    "description": "Strong and flexible, food-safe",
    "typical_density": 1.27,
    "typical_cost_per_kg": 25.00,
    "min_temp": 220,
    "max_temp": 250,
    "bed_temp": 70,
    "is_active": true
  }
]
```

### Create Material Type

Create a new material type.

```
POST /api/v1/spools/material-types
```

**Request Body:**

```json
{
  "code": "TPU",
  "name": "TPU (Thermoplastic Polyurethane)",
  "description": "Flexible, rubber-like material",
  "typical_density": 1.21,
  "typical_cost_per_kg": 35.00,
  "min_temp": 220,
  "max_temp": 250,
  "bed_temp": 50,
  "is_active": true
}
```

**Response: 201 Created**

Returns the created material type.

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Material type code already exists |

---

## Code Examples

### Python: Update Spool Weight

```python
import httpx

async def update_spool_weight(spool_id: str, new_weight: float, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"https://api.batchivo.app/api/v1/spools/{spool_id}",
            json={"current_weight_g": new_weight},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: List Low Stock Spools

```javascript
async function getLowStockSpools(token) {
  const response = await fetch(
    "https://api.batchivo.app/api/v1/spools?low_stock_only=true",
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

### cURL: Create Spool

```bash
curl -X POST "https://api.batchivo.app/api/v1/spools" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "material_type_id": "123e4567-e89b-12d3-a456-426614174000",
    "brand": "Polymaker",
    "color": "Galaxy Black",
    "diameter_mm": 1.75,
    "initial_weight_g": 1000,
    "current_weight_g": 1000
  }'
```
