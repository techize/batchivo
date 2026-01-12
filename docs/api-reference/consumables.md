# Consumables API

Manage non-filament consumables inventory including packaging, hardware, and supplies. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

### Consumable Types
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/consumables/types | List consumable types |
| POST | /api/v1/consumables/types | Create consumable type |
| GET | /api/v1/consumables/types/{id} | Get consumable details |
| PUT | /api/v1/consumables/types/{id} | Update consumable type |
| DELETE | /api/v1/consumables/types/{id} | Delete consumable type |
| POST | /api/v1/consumables/types/{id}/adjust-stock | Adjust stock level |

### Purchases
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/consumables/purchases | List purchases |
| POST | /api/v1/consumables/purchases | Record purchase |
| GET | /api/v1/consumables/purchases/{id} | Get purchase details |
| DELETE | /api/v1/consumables/purchases/{id} | Delete purchase |

### Usage
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/consumables/usage | List usage records |
| POST | /api/v1/consumables/usage | Record usage |

### Alerts & Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/consumables/alerts/low-stock | Get low stock alerts |
| GET | /api/v1/consumables/categories | List categories |

---

## Consumable Types

### List Consumable Types

```
GET /api/v1/consumables/types
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| page_size | integer | 20 | Items per page (max: 100) |
| search | string | - | Search by SKU or name |
| category | string | - | Filter by category |
| is_active | boolean | - | Filter by active status |
| low_stock_only | boolean | false | Show only low stock items |

**Response: 200 OK**

```json
{
  "total": 25,
  "page": 1,
  "page_size": 20,
  "consumables": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "sku": "PKG-BOX-SM",
      "name": "Small Shipping Box",
      "description": "6x4x3 inch cardboard box",
      "category": "Packaging",
      "unit_of_measure": "each",
      "current_cost_per_unit": 0.45,
      "quantity_on_hand": 150,
      "reorder_point": 50,
      "reorder_quantity": 200,
      "preferred_supplier": "Uline",
      "supplier_sku": "S-4321",
      "supplier_url": "https://uline.com/...",
      "typical_lead_days": 5,
      "is_active": true,
      "is_low_stock": false,
      "stock_value": 67.50,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ]
}
```

### Create Consumable Type

```
POST /api/v1/consumables/types
```

**Request Body:**

```json
{
  "sku": "PKG-BUBBLE-MD",
  "name": "Medium Bubble Wrap",
  "description": "12\" x 100ft roll",
  "category": "Packaging",
  "unit_of_measure": "roll",
  "current_cost_per_unit": 12.99,
  "quantity_on_hand": 5,
  "reorder_point": 2,
  "reorder_quantity": 10,
  "preferred_supplier": "Amazon",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sku | string | Yes | Unique SKU (auto-uppercased) |
| name | string | Yes | Consumable name |
| description | string | No | Description |
| category | string | No | Category for grouping |
| unit_of_measure | string | No | Unit (each, roll, box, etc.) |
| current_cost_per_unit | decimal | No | Current cost per unit |
| quantity_on_hand | decimal | No | Current stock level |
| reorder_point | decimal | No | When to reorder |
| reorder_quantity | decimal | No | How much to reorder |
| preferred_supplier | string | No | Supplier name |
| supplier_sku | string | No | Supplier's SKU |
| supplier_url | string | No | Product URL |
| typical_lead_days | integer | No | Days to receive |
| is_active | boolean | No | Default: true |

### Adjust Stock

Manually adjust stock level with audit trail.

```
POST /api/v1/consumables/types/{consumable_id}/adjust-stock
```

**Request Body:**

```json
{
  "quantity_adjustment": -5,
  "reason": "inventory_count",
  "notes": "Physical count showed 5 less than system"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quantity_adjustment | decimal | Yes | Amount to add (positive) or remove (negative) |
| reason | string | Yes | Reason for adjustment |
| notes | string | No | Additional notes |

---

## Purchases

### Record Purchase

```
POST /api/v1/consumables/purchases
```

**Request Body:**

```json
{
  "consumable_type_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity_purchased": 200,
  "total_cost": 90.00,
  "supplier": "Uline",
  "order_reference": "ORD-12345",
  "purchase_url": "https://uline.com/orders/12345",
  "purchase_date": "2024-03-15",
  "notes": "Bulk order discount"
}
```

**Effects:**
- Creates purchase record
- Increases `quantity_on_hand` by quantity purchased
- Updates `current_cost_per_unit` to new cost

**Response: 201 Created**

```json
{
  "id": "aaa11111-e89b-12d3-a456-426614174000",
  "consumable_type_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity_purchased": 200,
  "total_cost": 90.00,
  "cost_per_unit": 0.45,
  "quantity_remaining": 200,
  "supplier": "Uline",
  "order_reference": "ORD-12345",
  "purchase_date": "2024-03-15",
  ...
}
```

### List Purchases

```
GET /api/v1/consumables/purchases
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| page_size | integer | 20 | Items per page |
| consumable_type_id | UUID | - | Filter by consumable |

---

## Usage

### Record Usage

Deduct consumables from stock.

```
POST /api/v1/consumables/usage
```

**Request Body:**

```json
{
  "consumable_type_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity_used": 5,
  "production_run_id": "bbb22222-e89b-12d3-a456-426614174000",
  "product_id": "ccc33333-e89b-12d3-a456-426614174000",
  "usage_type": "packaging",
  "notes": "Order #1234 packaging"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| consumable_type_id | UUID | Yes | Consumable to use |
| quantity_used | decimal | Yes | Quantity to deduct (positive) or return (negative) |
| production_run_id | UUID | No | Link to production run |
| product_id | UUID | No | Link to product |
| usage_type | string | No | Type of usage |
| notes | string | No | Usage notes |

---

## Low Stock Alerts

Get all consumables below their reorder point.

```
GET /api/v1/consumables/alerts/low-stock
```

**Response: 200 OK**

```json
[
  {
    "consumable_id": "550e8400-e29b-41d4-a716-446655440000",
    "sku": "PKG-BOX-SM",
    "name": "Small Shipping Box",
    "quantity_on_hand": 35,
    "reorder_point": 50,
    "reorder_quantity": 200,
    "preferred_supplier": "Uline",
    "stock_value": 15.75
  }
]
```

---

## Categories

Get all unique categories used in consumables.

```
GET /api/v1/consumables/categories
```

**Response: 200 OK**

```json
["Hardware", "Labels", "Packaging", "Tools"]
```

---

## Code Examples

### Python: Record Purchase and Check Stock

```python
import httpx

async def record_purchase_and_check(token: str, consumable_id: str, qty: int, cost: float):
    async with httpx.AsyncClient() as client:
        # Record purchase
        await client.post(
            "https://api.batchivo.app/api/v1/consumables/purchases",
            json={
                "consumable_type_id": consumable_id,
                "quantity_purchased": qty,
                "total_cost": cost
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check low stock alerts
        response = await client.get(
            "https://api.batchivo.app/api/v1/consumables/alerts/low-stock",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Adjust Stock

```javascript
async function adjustStock(consumableId, adjustment, reason, token) {
  const response = await fetch(
    `https://api.batchivo.app/api/v1/consumables/types/${consumableId}/adjust-stock`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        quantity_adjustment: adjustment,
        reason: reason
      })
    }
  );
  return response.json();
}
```

---

## Inventory Flow

1. **Create consumable type** with initial stock
2. **Record purchases** to increase stock
3. **Record usage** to decrease stock
4. **Stock adjustments** for corrections
5. **Low stock alerts** trigger reorder reminders

All stock changes are tracked with timestamps and reasons for audit purposes.
