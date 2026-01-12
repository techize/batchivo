# Sales Channels API

Manage sales channels for multi-platform selling with platform-specific fee calculation. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/sales-channels | List all sales channels |
| POST | /api/v1/sales-channels | Create a sales channel |
| GET | /api/v1/sales-channels/{id} | Get channel details |
| PUT | /api/v1/sales-channels/{id} | Update a sales channel |
| DELETE | /api/v1/sales-channels/{id} | Delete a sales channel |

---

## Platform Types

The following platform types are supported:

| Platform | Description |
|----------|-------------|
| `fair` | In-person fair or market sales |
| `online_shop` | Own website/shop |
| `shopify` | Shopify store |
| `ebay` | eBay marketplace |
| `etsy` | Etsy marketplace |
| `amazon` | Amazon marketplace |
| `other` | Other platforms |

---

## List Sales Channels

Retrieve all sales channels with pagination and filtering.

```
GET /api/v1/sales-channels
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of items to skip |
| limit | integer | 100 | Max items to return (max: 1000) |
| search | string | - | Search by name |
| platform_type | string | - | Filter by platform type |
| is_active | boolean | - | Filter by active status |

**Response: 200 OK**

```json
{
  "channels": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Etsy Shop",
      "platform_type": "etsy",
      "base_fee_percent": 6.5,
      "payment_processing_percent": 3.0,
      "listing_fee": 0.20,
      "currency": "GBP",
      "url": "https://etsy.com/shop/myshop",
      "notes": "Main online sales channel",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Local Craft Fair",
      "platform_type": "fair",
      "base_fee_percent": 0.0,
      "payment_processing_percent": 2.5,
      "listing_fee": 0.0,
      "currency": "GBP",
      "url": null,
      "notes": "Monthly market at town hall",
      "is_active": true,
      "created_at": "2024-02-01T10:30:00Z",
      "updated_at": "2024-02-01T10:30:00Z"
    }
  ],
  "total": 5
}
```

---

## Create Sales Channel

Create a new sales channel.

```
POST /api/v1/sales-channels
```

**Request Body:**

```json
{
  "name": "Amazon UK",
  "platform_type": "amazon",
  "base_fee_percent": 15.0,
  "payment_processing_percent": 0.0,
  "listing_fee": 0.0,
  "currency": "GBP",
  "url": "https://amazon.co.uk/seller/myshop",
  "notes": "Amazon seller account",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Channel name (unique per tenant) |
| platform_type | string | Yes | One of the supported platform types |
| base_fee_percent | decimal | No | Platform fee percentage |
| payment_processing_percent | decimal | No | Payment processing fee % |
| listing_fee | decimal | No | Per-listing fee |
| currency | string | No | Currency code (default: GBP) |
| url | string | No | Shop/seller URL |
| notes | string | No | Additional notes |
| is_active | boolean | No | Default: true |

**Response: 201 Created**

Returns the created sales channel object.

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Name already exists or invalid platform type |

---

## Get Sales Channel

Get sales channel details by ID.

```
GET /api/v1/sales-channels/{channel_id}
```

**Response: 200 OK**

Returns full sales channel object.

---

## Update Sales Channel

Update sales channel properties.

```
PUT /api/v1/sales-channels/{channel_id}
```

**Request Body:**

```json
{
  "name": "Etsy Shop - Primary",
  "base_fee_percent": 6.5,
  "notes": "Updated fee structure"
}
```

All fields are optional - only provided fields are updated.

---

## Delete Sales Channel

Delete a sales channel (soft or hard delete).

```
DELETE /api/v1/sales-channels/{channel_id}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| permanent | boolean | false | Permanently delete (vs soft delete) |

**Response: 204 No Content**

---

## Code Examples

### Python: Create Channel with Fees

```python
import httpx

async def create_etsy_channel(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.batchivo.app/api/v1/sales-channels",
            json={
                "name": "Etsy Shop",
                "platform_type": "etsy",
                "base_fee_percent": 6.5,
                "payment_processing_percent": 3.0,
                "listing_fee": 0.20,
                "currency": "GBP"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: List Active Channels

```javascript
async function getActiveChannels(token) {
  const response = await fetch(
    "https://api.batchivo.app/api/v1/sales-channels?is_active=true",
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

---

## Fee Calculation

When products have pricing set for a sales channel, fees are calculated as:

```
Platform Fee = List Price × (base_fee_percent / 100)
Processing Fee = List Price × (payment_processing_percent / 100)
Total Fees = Platform Fee + Processing Fee + listing_fee
Net Revenue = List Price - Total Fees
```

This is used in product pricing to calculate profit margins per channel.
