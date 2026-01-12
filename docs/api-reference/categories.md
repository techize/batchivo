# Categories API

Manage product categories for organization and shop display. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/categories | List all categories |
| POST | /api/v1/categories | Create a category |
| GET | /api/v1/categories/{id} | Get category details |
| PATCH | /api/v1/categories/{id} | Update a category |
| DELETE | /api/v1/categories/{id} | Delete a category |

### Category Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/categories/{id}/products | List products in category |
| POST | /api/v1/categories/{id}/products/{product_id} | Add product to category |
| DELETE | /api/v1/categories/{id}/products/{product_id} | Remove product from category |

---

## List Categories

Retrieve all categories with pagination and filtering.

```
GET /api/v1/categories
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 50 | Items per page (max: 100) |
| include_inactive | boolean | false | Include inactive categories |
| search | string | - | Search by name |

**Response: 200 OK**

```json
{
  "categories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Miniatures",
      "slug": "miniatures",
      "description": "Tabletop gaming miniatures and figurines",
      "display_order": 1,
      "is_active": true,
      "product_count": 45,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Terrain",
      "slug": "terrain",
      "description": "Terrain pieces and scenery",
      "display_order": 2,
      "is_active": true,
      "product_count": 28,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ],
  "total": 8
}
```

---

## Create Category

Create a new category.

```
POST /api/v1/categories
```

**Request Body:**

```json
{
  "name": "Dice Towers",
  "slug": "dice-towers",
  "description": "Decorative dice towers for tabletop gaming",
  "display_order": 5,
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Category name |
| slug | string | No | URL-friendly slug (auto-generated if not provided) |
| description | string | No | Category description |
| display_order | integer | No | Sort order for display |
| is_active | boolean | No | Default: true |

**Response: 201 Created**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Dice Towers",
  "slug": "dice-towers",
  "description": "Decorative dice towers for tabletop gaming",
  "display_order": 5,
  "is_active": true,
  "product_count": 0,
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z"
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 409 | Category with slug already exists |

---

## Get Category

Get category details by ID.

```
GET /api/v1/categories/{category_id}
```

**Response: 200 OK**

Returns category object with product count.

---

## Update Category

Update category properties.

```
PATCH /api/v1/categories/{category_id}
```

**Request Body:**

```json
{
  "name": "Dice Towers & Accessories",
  "display_order": 3
}
```

All fields are optional - only provided fields are updated.

**Response: 200 OK**

Returns the updated category object.

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Category not found |
| 409 | Slug already exists |

---

## Delete Category

Delete a category (soft delete by default).

```
DELETE /api/v1/categories/{category_id}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| hard_delete | boolean | false | Permanently delete (vs soft delete) |

**Response: 204 No Content**

**Note:** Soft delete sets `is_active=false`. Hard delete permanently removes the category and its product associations.

---

## List Category Products

Get products assigned to a category.

```
GET /api/v1/categories/{category_id}/products
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 50 | Items per page (max: 100) |

**Response: 200 OK**

```json
{
  "products": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "sku": "DRAGON-001",
      "name": "Dragon Miniature"
    },
    {
      "id": "bbb22222-e89b-12d3-a456-426614174000",
      "sku": "DRAGON-002",
      "name": "Dragon Miniature - Large"
    }
  ],
  "total": 15
}
```

---

## Add Product to Category

Assign a product to a category.

```
POST /api/v1/categories/{category_id}/products/{product_id}
```

**Response: 204 No Content**

**Notes:**
- Products can belong to multiple categories
- If product is already in category, request is a no-op (returns 204)

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Category or product not found |

---

## Remove Product from Category

Remove a product from a category.

```
DELETE /api/v1/categories/{category_id}/products/{product_id}
```

**Response: 204 No Content**

---

## Code Examples

### Python: Create Category and Add Products

```python
import httpx

async def create_category_with_products(token: str, category_data: dict, product_ids: list):
    async with httpx.AsyncClient() as client:
        # Create category
        response = await client.post(
            "https://api.batchivo.app/api/v1/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        category = response.json()

        # Add products
        for product_id in product_ids:
            await client.post(
                f"https://api.batchivo.app/api/v1/categories/{category['id']}/products/{product_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

        return category
```

### JavaScript: List Categories

```javascript
async function getCategories(token, includeInactive = false) {
  const params = new URLSearchParams({ include_inactive: includeInactive });
  const response = await fetch(
    `https://api.batchivo.app/api/v1/categories?${params}`,
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  return response.json();
}
```

### cURL: Update Category

```bash
curl -X PATCH "https://api.batchivo.app/api/v1/categories/CATEGORY_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "display_order": 1
  }'
```

---

## Usage Notes

### Slugs

- Slugs are URL-friendly identifiers (lowercase, hyphens instead of spaces)
- Auto-generated from name if not provided
- Must be unique per tenant
- Used for public shop URLs (e.g., `/shop/categories/miniatures`)

### Display Order

- Lower numbers appear first
- Categories with same display_order sorted alphabetically
- Use for custom ordering in shop navigation

### Product Associations

- Products can belong to multiple categories
- Category deletion does not delete products
- Hard delete removes category-product associations
