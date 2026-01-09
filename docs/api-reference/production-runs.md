# Production Runs API

Track 3D print production runs with filament usage, multi-plate support, and inventory management. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

### Production Runs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/production-runs | List production runs |
| POST | /api/v1/production-runs | Create a production run |
| GET | /api/v1/production-runs/{id} | Get production run details |
| PATCH | /api/v1/production-runs/{id} | Update a production run |
| DELETE | /api/v1/production-runs/{id} | Delete a production run |
| POST | /api/v1/production-runs/{id}/complete | Complete and deduct inventory |
| POST | /api/v1/production-runs/{id}/cancel | Cancel production run |
| POST | /api/v1/production-runs/{id}/fail | Mark as failed with waste |
| GET | /api/v1/production-runs/failure-reasons | Get failure reason options |

### Production Run Items
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/production-runs/{id}/items | Add item to run |
| PATCH | /api/v1/production-runs/{id}/items/{item_id} | Update item |
| DELETE | /api/v1/production-runs/{id}/items/{item_id} | Remove item |

### Production Run Materials
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/production-runs/{id}/materials | Add material/spool |
| PATCH | /api/v1/production-runs/{id}/materials/{mat_id} | Update material |
| DELETE | /api/v1/production-runs/{id}/materials/{mat_id} | Remove material |

### Production Run Plates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/production-runs/{id}/plates | List plates |
| POST | /api/v1/production-runs/{id}/plates | Create plate |
| GET | /api/v1/production-runs/{id}/plates/{plate_id} | Get plate details |
| PATCH | /api/v1/production-runs/{id}/plates/{plate_id} | Update plate |
| POST | /api/v1/production-runs/{id}/plates/{plate_id}/start | Start printing |
| POST | /api/v1/production-runs/{id}/plates/{plate_id}/complete | Mark complete |
| POST | /api/v1/production-runs/{id}/plates/{plate_id}/fail | Mark failed |
| POST | /api/v1/production-runs/{id}/plates/{plate_id}/cancel | Cancel plate |
| DELETE | /api/v1/production-runs/{id}/plates/{plate_id} | Delete plate |

---

## List Production Runs

Retrieve production runs with filtering and pagination.

```
GET /api/v1/production-runs
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status_filter | string | - | Filter by status (in_progress, completed, failed, cancelled) |
| start_date | datetime | - | Filter runs started on or after |
| end_date | datetime | - | Filter runs started on or before |
| skip | integer | 0 | Pagination offset |
| limit | integer | 100 | Max results (max: 1000) |

**Response: 200 OK**

```json
{
  "total": 25,
  "skip": 0,
  "limit": 100,
  "runs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "run_number": "20240315-001",
      "status": "in_progress",
      "started_at": "2024-03-15T08:00:00Z",
      "completed_at": null,
      "duration_hours": null,
      "notes": "Dragon miniatures batch",
      "created_at": "2024-03-15T08:00:00Z"
    }
  ]
}
```

---

## Create Production Run

Create a new production run with items and materials.

```
POST /api/v1/production-runs
```

**Request Body:**

```json
{
  "run_number": "20240315-001",
  "started_at": "2024-03-15T08:00:00Z",
  "notes": "Dragon miniatures batch",
  "items": [
    {
      "model_id": "111e2222-e89b-12d3-a456-426614174000",
      "quantity": 5
    }
  ],
  "materials": [
    {
      "spool_id": "222e3333-e89b-12d3-a456-426614174000",
      "estimated_model_weight_grams": 150,
      "estimated_flushed_grams": 10,
      "estimated_tower_grams": 25
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| run_number | string | No | Auto-generated as YYYYMMDD-NNN if not provided |
| started_at | datetime | No | Defaults to now |
| notes | string | No | Run notes |
| items | array | Yes | Models being printed |
| materials | array | Yes | Spools being used |

**Material Validation:**
- Checks spool has sufficient inventory for estimated total usage
- Total estimated = model_weight + flushed + tower

**Response: 201 Created**

Returns full production run with items and materials.

---

## Get Production Run

Get detailed information including items and materials with their relationships.

```
GET /api/v1/production-runs/{run_id}
```

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "run_number": "20240315-001",
  "status": "in_progress",
  "started_at": "2024-03-15T08:00:00Z",
  "completed_at": null,
  "duration_hours": null,
  "actual_total_filament_grams": null,
  "notes": "Dragon miniatures batch",
  "items": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "model_id": "111e2222-e89b-12d3-a456-426614174000",
      "quantity": 5,
      "model": {
        "id": "111e2222-e89b-12d3-a456-426614174000",
        "name": "Dragon Miniature",
        "sku": "MDL-DRAGON-001"
      }
    }
  ],
  "materials": [
    {
      "id": "bbb22222-e89b-12d3-a456-426614174000",
      "spool_id": "222e3333-e89b-12d3-a456-426614174000",
      "estimated_model_weight_grams": 150,
      "estimated_flushed_grams": 10,
      "estimated_tower_grams": 25,
      "actual_model_weight_grams": null,
      "spool_weight_before_grams": null,
      "spool_weight_after_grams": null,
      "spool": {
        "id": "222e3333-e89b-12d3-a456-426614174000",
        "spool_id": "FIL-001",
        "brand": "Bambu Lab",
        "color": "Matte Black",
        "material_type": {
          "code": "PLA",
          "name": "PLA"
        }
      }
    }
  ]
}
```

---

## Update Production Run

Update a production run. Completed/failed/cancelled runs only allow updating notes.

```
PATCH /api/v1/production-runs/{run_id}
```

**Request Body:**

```json
{
  "notes": "Updated notes",
  "completed_at": "2024-03-15T12:30:00Z"
}
```

Duration is auto-calculated when `completed_at` is set.

---

## Complete Production Run

Mark as completed and deduct actual usage from spool inventory.

```
POST /api/v1/production-runs/{run_id}/complete
```

**Prerequisites:**
All materials must have actual usage recorded via either:
- Weighing: `spool_weight_before_grams` and `spool_weight_after_grams`
- Manual: `actual_model_weight_grams`

**Response: 200 OK**

Returns completed production run with:
- Status set to "completed"
- completed_at timestamp
- duration_hours calculated
- actual_total_filament_grams summed

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Already completed |
| 400 | Material missing actual usage |
| 400 | Insufficient inventory for deduction |

---

## Cancel Production Run

Cancel a production run with options for material handling.

```
POST /api/v1/production-runs/{run_id}/cancel
```

**Request Body:**

```json
{
  "cancel_mode": "full_reversal",
  "partial_usage": null
}
```

**Cancel Modes:**

| Mode | Description |
|------|-------------|
| full_reversal | Cancel without deducting any materials |
| record_partial | Deduct specified partial usage amounts |

**For record_partial mode:**

```json
{
  "cancel_mode": "record_partial",
  "partial_usage": [
    {
      "spool_id": "222e3333-e89b-12d3-a456-426614174000",
      "grams": 50
    }
  ]
}
```

---

## Fail Production Run

Mark as failed and record waste materials.

```
POST /api/v1/production-runs/{run_id}/fail
```

**Request Body:**

```json
{
  "failure_reason": "layer_adhesion",
  "waste_materials": [
    {
      "spool_id": "222e3333-e89b-12d3-a456-426614174000",
      "grams": 75
    }
  ],
  "notes": "Failed at layer 50 due to adhesion issue"
}
```

This:
1. Records waste as WASTE transaction type
2. Deducts waste from spool inventory
3. Sets status to "failed" with failure reason

---

## Get Failure Reasons

Get predefined failure reason options for UI dropdowns.

```
GET /api/v1/production-runs/failure-reasons
```

**Response: 200 OK**

```json
[
  {
    "value": "layer_adhesion",
    "label": "Layer Adhesion Failure",
    "description": "Layers not bonding properly"
  },
  {
    "value": "bed_adhesion",
    "label": "Bed Adhesion Failure",
    "description": "Print detached from bed"
  },
  {
    "value": "stringing",
    "label": "Excessive Stringing",
    "description": "Too much stringing between parts"
  }
]
```

---

## Production Run Items

### Add Item

```
POST /api/v1/production-runs/{run_id}/items
```

**Request Body:**

```json
{
  "model_id": "111e2222-e89b-12d3-a456-426614174000",
  "quantity": 3
}
```

### Update Item

```
PATCH /api/v1/production-runs/{run_id}/items/{item_id}
```

**Request Body:**

```json
{
  "quantity": 5
}
```

Cannot update items for completed/failed/cancelled runs.

### Delete Item

```
DELETE /api/v1/production-runs/{run_id}/items/{item_id}
```

---

## Production Run Materials

### Add Material

```
POST /api/v1/production-runs/{run_id}/materials
```

**Request Body:**

```json
{
  "spool_id": "222e3333-e89b-12d3-a456-426614174000",
  "estimated_model_weight_grams": 100,
  "estimated_flushed_grams": 5,
  "estimated_tower_grams": 15
}
```

Validates sufficient inventory for estimated total.

### Update Material

```
PATCH /api/v1/production-runs/{run_id}/materials/{material_id}
```

**Request Body (Recording Actuals):**

```json
{
  "spool_weight_before_grams": 750,
  "spool_weight_after_grams": 630,
  "actual_model_weight_grams": 100,
  "actual_flushed_grams": 8,
  "actual_tower_grams": 12
}
```

### Delete Material

```
DELETE /api/v1/production-runs/{run_id}/materials/{material_id}
```

---

## Production Run Plates

Multi-plate support for batch printing.

### Create Plate

```
POST /api/v1/production-runs/{run_id}/plates
```

**Request Body:**

```json
{
  "plate_number": 1,
  "model_id": "111e2222-e89b-12d3-a456-426614174000",
  "printer_id": "333e4444-e89b-12d3-a456-426614174000",
  "copies_per_plate": 4,
  "estimated_print_time_minutes": 120,
  "notes": "First plate of dragon minis"
}
```

### List Plates

```
GET /api/v1/production-runs/{run_id}/plates?status_filter=printing
```

### Start Plate

Transition from pending to printing.

```
POST /api/v1/production-runs/{run_id}/plates/{plate_id}/start
```

### Complete Plate

```
POST /api/v1/production-runs/{run_id}/plates/{plate_id}/complete
```

**Request Body:**

```json
{
  "successful_prints": 4,
  "failed_prints": 0,
  "notes": "All prints successful"
}
```

### Fail/Cancel Plate

```
POST /api/v1/production-runs/{run_id}/plates/{plate_id}/fail
POST /api/v1/production-runs/{run_id}/plates/{plate_id}/cancel
```

Optional query parameter: `notes`

---

## Code Examples

### Python: Create and Complete Production Run

```python
import httpx

async def create_production_run(token: str, items: list, materials: list):
    async with httpx.AsyncClient() as client:
        # Create run
        response = await client.post(
            "https://api.nozzly.app/api/v1/production-runs",
            json={
                "notes": "Batch production",
                "items": items,
                "materials": materials
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        run = response.json()
        return run

async def complete_run(token: str, run_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.nozzly.app/api/v1/production-runs/{run_id}/complete",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Track Material Usage

```javascript
async function recordMaterialUsage(runId, materialId, beforeWeight, afterWeight, token) {
  const response = await fetch(
    `https://api.nozzly.app/api/v1/production-runs/${runId}/materials/${materialId}`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        spool_weight_before_grams: beforeWeight,
        spool_weight_after_grams: afterWeight
      })
    }
  );
  return response.json();
}
```

### cURL: Complete Production Run

```bash
# First, update material with actual weights
curl -X PATCH "https://api.nozzly.app/api/v1/production-runs/RUN_ID/materials/MATERIAL_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "spool_weight_before_grams": 750,
    "spool_weight_after_grams": 630
  }'

# Then complete the run
curl -X POST "https://api.nozzly.app/api/v1/production-runs/RUN_ID/complete" \
  -H "Authorization: Bearer YOUR_TOKEN"
```
