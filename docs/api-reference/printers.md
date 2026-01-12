# Printers API

Manage 3D printers and machines. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/printers | List all printers |
| POST | /api/v1/printers | Create a new printer |
| GET | /api/v1/printers/{id} | Get printer details |
| PUT | /api/v1/printers/{id} | Update a printer |
| DELETE | /api/v1/printers/{id} | Delete a printer |

---

## List Printers

Retrieve all printers with pagination and filtering.

```
GET /api/v1/printers
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of items to skip |
| limit | integer | 100 | Max items to return (max: 1000) |
| is_active | boolean | - | Filter by active status |

**Response: 200 OK**

```json
{
  "total": 5,
  "skip": 0,
  "limit": 100,
  "printers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Bambu Lab X1 Carbon",
      "model": "X1 Carbon",
      "manufacturer": "Bambu Lab",
      "serial_number": "BL12345678",
      "build_volume_x": 256,
      "build_volume_y": 256,
      "build_volume_z": 256,
      "nozzle_diameter": 0.4,
      "heated_bed": true,
      "enclosure": true,
      "multi_material": true,
      "max_material_count": 4,
      "hourly_rate": 2.50,
      "location": "Workshop A",
      "notes": "Primary production printer",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ]
}
```

---

## Create Printer

Create a new printer entry.

```
POST /api/v1/printers
```

**Request Body:**

```json
{
  "name": "Bambu Lab X1 Carbon",
  "model": "X1 Carbon",
  "manufacturer": "Bambu Lab",
  "serial_number": "BL12345678",
  "build_volume_x": 256,
  "build_volume_y": 256,
  "build_volume_z": 256,
  "nozzle_diameter": 0.4,
  "heated_bed": true,
  "enclosure": true,
  "multi_material": true,
  "max_material_count": 4,
  "hourly_rate": 2.50,
  "location": "Workshop A",
  "notes": "Primary production printer",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Printer name/identifier |
| model | string | No | Printer model name |
| manufacturer | string | No | Manufacturer name |
| serial_number | string | No | Serial number |
| build_volume_x | decimal | No | Build volume X (mm) |
| build_volume_y | decimal | No | Build volume Y (mm) |
| build_volume_z | decimal | No | Build volume Z (mm) |
| nozzle_diameter | decimal | No | Nozzle diameter (mm) |
| heated_bed | boolean | No | Has heated bed |
| enclosure | boolean | No | Has enclosure |
| multi_material | boolean | No | Multi-material capable |
| max_material_count | integer | No | Max simultaneous materials |
| hourly_rate | decimal | No | Operating cost per hour |
| location | string | No | Physical location |
| notes | string | No | Additional notes |
| is_active | boolean | No | Default: true |

**Response: 201 Created**

Returns the created printer object.

---

## Get Printer

Get printer details by ID.

```
GET /api/v1/printers/{printer_id}
```

**Response: 200 OK**

Returns full printer object.

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Printer not found |

---

## Update Printer

Update printer properties.

```
PUT /api/v1/printers/{printer_id}
```

**Request Body:**

```json
{
  "name": "Bambu Lab X1 Carbon - Primary",
  "hourly_rate": 3.00,
  "location": "Workshop B"
}
```

All fields are optional - only provided fields are updated.

**Response: 200 OK**

Returns the updated printer object.

---

## Delete Printer

Soft delete a printer (sets is_active=false).

```
DELETE /api/v1/printers/{printer_id}
```

**Response: 204 No Content**

---

## Code Examples

### Python: List Active Printers

```python
import httpx

async def get_active_printers(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.batchivo.app/api/v1/printers",
            params={"is_active": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Create Printer

```javascript
async function createPrinter(printerData, token) {
  const response = await fetch(
    "https://api.batchivo.app/api/v1/printers",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(printerData)
    }
  );
  return response.json();
}
```

### cURL: Update Printer

```bash
curl -X PUT "https://api.batchivo.app/api/v1/printers/PRINTER_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hourly_rate": 3.50,
    "notes": "Updated hourly rate for electricity costs"
  }'
```

---

## Usage Notes

### Printer Costs

The `hourly_rate` field is used in production run cost calculations:
- Machine time cost = print time (hours) × hourly rate
- Include electricity, depreciation, and maintenance in the hourly rate

### Multi-Material Support

For printers with AMS or multi-material systems:
- Set `multi_material: true`
- Set `max_material_count` to the number of filament slots
- This enables multi-color production run tracking

### Build Volume

Build volume dimensions help validate that models will fit:
- Used by production planning features
- Dimensions are in millimeters
