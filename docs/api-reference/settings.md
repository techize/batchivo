# Settings API

Manage tenant configuration and integrations. Requires authentication with admin/owner role for modifications.

## Endpoints Summary

### Square Payment Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/settings/square | Get Square settings |
| PUT | /api/v1/settings/square | Update Square settings |
| POST | /api/v1/settings/square/test | Test Square connection |

### Tenant Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/settings/tenant | Get tenant details |
| PUT | /api/v1/settings/tenant | Update tenant details |

---

## Authorization

Settings modification requires **Admin** or **Owner** role. Read operations require authentication.

---

## Square Payment Settings

### Get Square Settings

Get current Square payment gateway configuration with masked credentials.

```
GET /api/v1/settings/square
```

**Response: 200 OK**

```json
{
  "is_configured": true,
  "environment": "production",
  "application_id_masked": "****ABCD",
  "access_token_masked": "****WXYZ",
  "location_id": "LABCDEF123456",
  "location_name": "My 3D Print Shop",
  "webhook_signature_key_masked": "****1234",
  "last_tested_at": "2024-03-15T10:30:00Z",
  "test_status": "success"
}
```

**Note:** Sensitive values are masked, showing only the last 4 characters.

### Update Square Settings

Update Square payment gateway credentials.

```
PUT /api/v1/settings/square
```

**Required Role:** Admin or Owner

**Request Body:**

```json
{
  "environment": "production",
  "application_id": "sq0idp-XXXXXXXXXXXXXXXXXXXX",
  "access_token": "EAAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "location_id": "LABCDEF123456",
  "webhook_signature_key": "webhook-signature-key-here"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| environment | string | No | "sandbox" or "production" |
| application_id | string | No | Square application ID |
| access_token | string | No | Square access token |
| location_id | string | No | Square location ID |
| webhook_signature_key | string | No | Webhook signature verification key |

**Note:** All credentials are encrypted before storage.

### Test Square Connection

Test Square API connection with current credentials.

```
POST /api/v1/settings/square/test
```

**Required Role:** Admin or Owner

**Response: 200 OK**

```json
{
  "success": true,
  "location_name": "My 3D Print Shop",
  "location_currency": "GBP",
  "error_message": null
}
```

**On Failure:**

```json
{
  "success": false,
  "location_name": null,
  "location_currency": null,
  "error_message": "Invalid access token or location ID"
}
```

---

## Tenant Settings

### Get Tenant Details

Get current tenant information.

```
GET /api/v1/settings/tenant
```

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Mystmere Forge",
  "slug": "mystmere-forge",
  "description": "Fantasy miniatures and terrain",
  "logo_url": "/uploads/tenants/mystmere-logo.png",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-03-15T10:30:00Z"
}
```

### Update Tenant Details

Update tenant name and description.

```
PUT /api/v1/settings/tenant
```

**Required Role:** Admin or Owner

**Request Body:**

```json
{
  "name": "Mystmere Forge Ltd",
  "description": "Premium fantasy miniatures and modular terrain"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | Tenant display name |
| description | string | No | Tenant description |

---

## Code Examples

### Python: Configure Square

```python
import httpx

async def configure_square(token: str, square_config: dict):
    async with httpx.AsyncClient() as client:
        # Update settings
        response = await client.put(
            "https://api.nozzly.app/api/v1/settings/square",
            json=square_config,
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            # Test connection
            test_response = await client.post(
                "https://api.nozzly.app/api/v1/settings/square/test",
                headers={"Authorization": f"Bearer {token}"}
            )
            return test_response.json()

        return response.json()
```

### JavaScript: Get Settings

```javascript
async function getSettings(token) {
  const [square, tenant] = await Promise.all([
    fetch("https://api.nozzly.app/api/v1/settings/square", {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()),

    fetch("https://api.nozzly.app/api/v1/settings/tenant", {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json())
  ]);

  return { square, tenant };
}
```

---

## Security Notes

### Credential Storage

- All payment credentials are encrypted at rest using AES-256
- Credentials are never logged or returned in full
- Only masked values (last 4 characters) are shown in API responses

### Role Requirements

| Operation | Required Role |
|-----------|---------------|
| View settings | Any authenticated user |
| Modify settings | Admin or Owner |
| Test connections | Admin or Owner |

### Square Environment

- Use `sandbox` for testing with Square's test credentials
- Switch to `production` for live payments
- Test connection after any credential changes
