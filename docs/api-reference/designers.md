# Designers API

Manage designer/creator profiles for product attribution and membership tracking. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/designers | List all designers |
| POST | /api/v1/designers | Create a designer |
| GET | /api/v1/designers/{id} | Get designer details |
| PATCH | /api/v1/designers/{id} | Update a designer |
| DELETE | /api/v1/designers/{id} | Delete a designer |

---

## List Designers

Retrieve all designers with pagination and filtering.

```
GET /api/v1/designers
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 50 | Items per page (max: 100) |
| include_inactive | boolean | false | Include inactive designers |
| search | string | - | Search by name |

**Response: 200 OK**

```json
{
  "designers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Epic Miniatures",
      "slug": "epic-miniatures",
      "description": "High-quality fantasy miniatures for tabletop gaming",
      "logo_url": "/uploads/designers/epic-minis-logo.png",
      "website_url": "https://epicminiatures.com",
      "social_links": {
        "instagram": "epicminis",
        "twitter": "epicminiatures",
        "patreon": "epicminiatures"
      },
      "membership_cost": 15.00,
      "membership_start_date": "2024-01-01",
      "membership_renewal_date": "2025-01-01",
      "is_active": true,
      "notes": "Patreon supporter tier",
      "product_count": 45,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ],
  "total": 12
}
```

---

## Create Designer

Create a new designer profile.

```
POST /api/v1/designers
```

**Request Body:**

```json
{
  "name": "Loot Studios",
  "slug": "loot-studios",
  "description": "Monthly fantasy miniature releases",
  "logo_url": "/uploads/designers/loot-logo.png",
  "website_url": "https://lootstudios.com",
  "social_links": {
    "instagram": "lootstudios",
    "patreon": "lootstudios"
  },
  "membership_cost": 20.00,
  "membership_start_date": "2024-03-01",
  "membership_renewal_date": "2025-03-01",
  "is_active": true,
  "notes": "Hero tier subscription"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Designer name |
| slug | string | No | URL-friendly slug (auto-generated if not provided) |
| description | string | No | Designer description |
| logo_url | string | No | Path to logo image |
| website_url | string | No | Designer website |
| social_links | object | No | Social media links (key-value pairs) |
| membership_cost | decimal | No | Monthly/annual membership cost |
| membership_start_date | date | No | When membership started |
| membership_renewal_date | date | No | When membership renews |
| is_active | boolean | No | Default: true |
| notes | string | No | Internal notes |

**Response: 201 Created**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Loot Studios",
  "slug": "loot-studios",
  "product_count": 0,
  ...
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 409 | Designer with slug already exists |

---

## Get Designer

Get designer details by ID.

```
GET /api/v1/designers/{designer_id}
```

**Response: 200 OK**

Returns designer object with product count.

---

## Update Designer

Update designer properties.

```
PATCH /api/v1/designers/{designer_id}
```

**Request Body:**

```json
{
  "membership_cost": 25.00,
  "membership_renewal_date": "2025-06-01",
  "notes": "Upgraded to premium tier"
}
```

All fields are optional - only provided fields are updated.

---

## Delete Designer

Delete a designer (hard delete).

```
DELETE /api/v1/designers/{designer_id}
```

**Response: 204 No Content**

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Designer not found |
| 409 | Cannot delete designer with associated products |

**Note:** Designers with associated products cannot be deleted. Either remove the products first or set the designer to inactive.

---

## Code Examples

### Python: Create Designer with Social Links

```python
import httpx

async def create_designer(token: str, designer_data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.batchivo.app/api/v1/designers",
            json={
                "name": "Epic Miniatures",
                "website_url": "https://epicminiatures.com",
                "social_links": {
                    "instagram": "epicminis",
                    "patreon": "epicminiatures"
                },
                "membership_cost": 15.00
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: List Active Designers

```javascript
async function getActiveDesigners(token) {
  const response = await fetch(
    "https://api.batchivo.app/api/v1/designers?include_inactive=false",
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

---

## Usage Notes

### Membership Tracking

The membership fields help track subscription costs for designers:
- `membership_cost` - Monthly or annual cost
- `membership_start_date` - When you joined
- `membership_renewal_date` - When payment is due

This data can be used for:
- Cost allocation to products
- Membership renewal reminders
- ROI analysis per designer

### Social Links

The `social_links` field is a flexible JSON object. Common keys:
- `instagram`, `twitter`, `facebook`
- `patreon`, `kickstarter`
- `myminifactory`, `cults3d`, `thingiverse`
