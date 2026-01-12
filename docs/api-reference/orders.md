# Orders API

Manage customer orders including status tracking, shipping, and fulfillment. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/orders | List orders with filtering |
| GET | /api/v1/orders/counts | Get order counts by status |
| GET | /api/v1/orders/{id} | Get order details |
| PATCH | /api/v1/orders/{id} | Update order |
| POST | /api/v1/orders/{id}/ship | Mark order as shipped |

---

## List Orders

Retrieve orders with filtering and pagination.

```
GET /api/v1/orders
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | - | Filter by status |
| search | string | - | Search by order number, customer name, or email |
| date_from | date | - | Filter orders from this date |
| date_to | date | - | Filter orders to this date |
| page | integer | 1 | Page number |
| limit | integer | 20 | Items per page (max: 100) |

**Order Status Values:**
- `pending` - New order, awaiting processing
- `processing` - Being prepared
- `shipped` - Shipped to customer
- `delivered` - Delivered to customer
- `cancelled` - Cancelled
- `refunded` - Refunded

**Response: 200 OK**

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "order_number": "MYS-2024-0042",
      "status": "pending",
      "customer_email": "customer@example.com",
      "customer_name": "John Doe",
      "customer_phone": "+44 7123 456789",
      "shipping_address_line1": "123 Main St",
      "shipping_address_line2": "Apt 4",
      "shipping_city": "London",
      "shipping_county": "Greater London",
      "shipping_postcode": "SW1A 1AA",
      "shipping_country": "United Kingdom",
      "shipping_method": "standard",
      "shipping_cost": 4.99,
      "subtotal": 24.99,
      "total": 29.98,
      "currency": "GBP",
      "payment_provider": "square",
      "payment_id": "sq_payment_123",
      "payment_status": "captured",
      "tracking_number": null,
      "tracking_url": null,
      "shipped_at": null,
      "delivered_at": null,
      "fulfilled_at": null,
      "customer_notes": "Please leave at door",
      "internal_notes": null,
      "created_at": "2024-03-15T10:30:00Z",
      "updated_at": "2024-03-15T10:30:00Z",
      "items": [
        {
          "id": "111e2222-e89b-12d3-a456-426614174000",
          "product_id": "222e3333-e89b-12d3-a456-426614174000",
          "product_sku": "DRAGON-001",
          "product_name": "Dragon Miniature",
          "quantity": 2,
          "unit_price": 12.50,
          "total_price": 25.00
        }
      ]
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

---

## Get Order Counts

Get order counts grouped by status.

```
GET /api/v1/orders/counts
```

**Response: 200 OK**

```json
{
  "pending": 12,
  "processing": 5,
  "shipped": 8,
  "delivered": 125,
  "cancelled": 3,
  "refunded": 2,
  "total": 155
}
```

---

## Get Order

Get detailed information about a specific order.

```
GET /api/v1/orders/{order_id}
```

**Response: 200 OK**

Returns full order object with items.

---

## Update Order

Update order status, tracking information, or internal notes.

```
PATCH /api/v1/orders/{order_id}
```

**Request Body:**

```json
{
  "status": "processing",
  "tracking_number": "RM123456789GB",
  "tracking_url": "https://tracking.royalmail.com/RM123456789GB",
  "internal_notes": "Priority order - ship first"
}
```

| Field | Type | Description |
|-------|------|-------------|
| status | string | New order status |
| tracking_number | string | Shipping tracking number |
| tracking_url | string | Tracking URL |
| internal_notes | string | Internal staff notes |

---

## Ship Order

Mark an order as shipped with tracking information. Automatically fulfills the order (deducts inventory) if not already done.

```
POST /api/v1/orders/{order_id}/ship
```

**Request Body:**

```json
{
  "tracking_number": "RM123456789GB",
  "tracking_url": "https://tracking.royalmail.com/RM123456789GB"
}
```

**This endpoint:**
1. Sets status to "shipped"
2. Records shipped_at timestamp
3. Deducts inventory if not already fulfilled
4. Sends shipped notification email to customer

---

## Code Examples

### Python: List Pending Orders

```python
import httpx

async def get_pending_orders(token: str, page: int = 1):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.batchivo.app/api/v1/orders",
            params={"status": "pending", "page": page},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Ship Order

```javascript
async function shipOrder(orderId, trackingNumber, trackingUrl, token) {
  const response = await fetch(
    `https://api.batchivo.app/api/v1/orders/${orderId}/ship`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        tracking_number: trackingNumber,
        tracking_url: trackingUrl
      })
    }
  );
  return response.json();
}
```

### cURL: Search Orders

```bash
curl -X GET "https://api.batchivo.app/api/v1/orders?search=john@example.com&status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN"
```
