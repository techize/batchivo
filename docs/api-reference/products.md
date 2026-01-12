# Products API

Manage product catalog - sellable items composed of 3D models. All endpoints require authentication and return data scoped to the current tenant.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/products | List all products |
| POST | /api/v1/products | Create a new product |
| GET | /api/v1/products/{id} | Get product details |
| PUT | /api/v1/products/{id} | Update a product |
| DELETE | /api/v1/products/{id} | Delete a product |
| POST | /api/v1/products/{id}/models | Add model to product |
| PUT | /api/v1/products/{id}/models/{model_id} | Update model quantity |
| DELETE | /api/v1/products/{id}/models/{model_id} | Remove model from product |
| POST | /api/v1/products/{id}/pricing | Add pricing for channel |
| PUT | /api/v1/products/{id}/pricing/{pricing_id} | Update pricing |
| DELETE | /api/v1/products/{id}/pricing/{pricing_id} | Remove pricing |
| POST | /api/v1/products/{id}/components | Add child product (bundle) |
| PUT | /api/v1/products/{id}/components/{comp_id} | Update component quantity |
| DELETE | /api/v1/products/{id}/components/{comp_id} | Remove component |
| GET | /api/v1/products/{id}/images | List product images |
| POST | /api/v1/products/{id}/images | Upload image |
| PATCH | /api/v1/products/{id}/images/{img_id} | Update image metadata |
| POST | /api/v1/products/{id}/images/{img_id}/set-primary | Set primary image |
| POST | /api/v1/products/{id}/images/{img_id}/rotate | Rotate image |
| DELETE | /api/v1/products/{id}/images/{img_id} | Delete image |

---

## List Products

Retrieve all products with pagination, search, and filtering.

```
GET /api/v1/products
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of items to skip |
| limit | integer | 100 | Max items to return (max: 1000) |
| search | string | - | Full-text search by name, SKU, or description |
| is_active | boolean | - | Filter by active status |
| designer_id | UUID | - | Filter by designer |

**Response: 200 OK**

```json
{
  "total": 25,
  "skip": 0,
  "limit": 100,
  "products": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
      "sku": "PROD-001",
      "name": "Dragon Miniature",
      "description": "Detailed dragon figurine for tabletop gaming",
      "designer_id": "789e0123-e89b-12d3-a456-426614174000",
      "designer_name": "Epic Minis",
      "designer_slug": "epic-minis",
      "designer_logo_url": "/uploads/designers/epic-minis-logo.png",
      "packaging_cost": 1.50,
      "packaging_consumable_id": null,
      "packaging_quantity": 1,
      "assembly_minutes": 5,
      "units_in_stock": 10,
      "is_active": true,
      "shop_visible": true,
      "total_make_cost": 8.45,
      "suggested_price": 21.13,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ]
}
```

---

## Create Product

Create a new sellable product.

```
POST /api/v1/products
```

**Request Body:**

```json
{
  "sku": "PROD-042",
  "name": "Castle Tower Set",
  "description": "Modular castle tower with 3 floors",
  "designer_id": "789e0123-e89b-12d3-a456-426614174000",
  "packaging_cost": 2.00,
  "packaging_consumable_id": "456e7890-e89b-12d3-a456-426614174000",
  "packaging_quantity": 1,
  "assembly_minutes": 15,
  "units_in_stock": 0,
  "is_active": true,
  "shop_visible": false,
  "models": [
    {
      "model_id": "111e2222-e89b-12d3-a456-426614174000",
      "quantity": 3
    }
  ],
  "child_products": [
    {
      "child_product_id": "222e3333-e89b-12d3-a456-426614174000",
      "quantity": 1
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sku | string | Yes | Unique product SKU |
| name | string | Yes | Product name |
| description | string | No | Product description |
| designer_id | UUID | No | Designer for attribution |
| packaging_cost | decimal | No | Additional packaging cost |
| packaging_consumable_id | UUID | No | Link to consumable for packaging |
| packaging_quantity | integer | No | Quantity of packaging consumable |
| assembly_minutes | integer | No | Assembly time estimate |
| units_in_stock | integer | No | Current stock level |
| is_active | boolean | No | Default: true |
| shop_visible | boolean | No | Show in public shop |
| models | array | No | 3D models to include |
| child_products | array | No | Child products for bundles |

**Response: 201 Created**

Returns the full product detail including cost breakdown.

---

## Get Product

Retrieve detailed product information including models, pricing, and cost breakdown.

```
GET /api/v1/products/{product_id}
```

**Response: 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "sku": "PROD-001",
  "name": "Dragon Miniature",
  "description": "Detailed dragon figurine",
  "models": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "model_id": "bbb22222-e89b-12d3-a456-426614174000",
      "quantity": 1,
      "model_name": "Dragon Body",
      "model_sku": "MDL-DRAGON-001",
      "model_cost": 3.50,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "child_products": [],
  "pricing": [
    {
      "id": "ccc33333-e89b-12d3-a456-426614174000",
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "sales_channel_id": "ddd44444-e89b-12d3-a456-426614174000",
      "list_price": 24.99,
      "is_active": true,
      "channel_name": "Etsy Shop",
      "platform_type": "etsy",
      "platform_fee": 3.25,
      "net_revenue": 21.74,
      "profit": 13.29,
      "margin_percentage": 61.13,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-03-01T14:20:00Z"
    }
  ],
  "cost_breakdown": {
    "model_costs": [
      {
        "model_id": "bbb22222-e89b-12d3-a456-426614174000",
        "model_name": "Dragon Body",
        "quantity": 1,
        "unit_cost": 3.50,
        "total_cost": 3.50
      }
    ],
    "child_product_costs": [],
    "total_model_cost": 3.50,
    "total_child_product_cost": 0.00,
    "packaging_cost": 1.50,
    "assembly_cost": 1.25,
    "total_make_cost": 8.45
  },
  "categories": [
    {"id": "eee55555-e89b-12d3-a456-426614174000", "name": "Miniatures", "slug": "miniatures"}
  ],
  "designer_name": "Epic Minis",
  "designer_slug": "epic-minis"
}
```

---

## Update Product

Update product properties.

```
PUT /api/v1/products/{product_id}
```

**Request Body:**

```json
{
  "name": "Dragon Miniature - Large",
  "description": "Updated description",
  "units_in_stock": 15,
  "shop_visible": true
}
```

All fields are optional - only provided fields are updated.

---

## Delete Product

Soft delete a product (sets is_active=false).

```
DELETE /api/v1/products/{product_id}
```

**Response: 204 No Content**

---

## Product Models

Manage which 3D models are included in a product.

### Add Model to Product

```
POST /api/v1/products/{product_id}/models
```

**Request Body:**

```json
{
  "model_id": "bbb22222-e89b-12d3-a456-426614174000",
  "quantity": 2
}
```

### Update Model Quantity

```
PUT /api/v1/products/{product_id}/models/{product_model_id}
```

**Request Body:**

```json
{
  "model_id": "bbb22222-e89b-12d3-a456-426614174000",
  "quantity": 3
}
```

### Remove Model

```
DELETE /api/v1/products/{product_id}/models/{product_model_id}
```

---

## Product Pricing

Manage pricing per sales channel with automatic profit calculation.

### Add Pricing

```
POST /api/v1/products/{product_id}/pricing
```

**Request Body:**

```json
{
  "sales_channel_id": "ddd44444-e89b-12d3-a456-426614174000",
  "list_price": 29.99,
  "is_active": true
}
```

**Response includes calculated:**
- `platform_fee` - Channel fees
- `net_revenue` - After platform fees
- `profit` - After make cost
- `margin_percentage` - Profit margin

### Update Pricing

```
PUT /api/v1/products/{product_id}/pricing/{pricing_id}
```

### Remove Pricing

```
DELETE /api/v1/products/{product_id}/pricing/{pricing_id}
```

---

## Product Components (Bundles)

Create bundle products by adding child products.

### Add Child Product

```
POST /api/v1/products/{product_id}/components
```

**Request Body:**

```json
{
  "child_product_id": "222e3333-e89b-12d3-a456-426614174000",
  "quantity": 2
}
```

**Validation:**
- Cannot add a product to itself
- Circular references are detected and rejected (A cannot contain B if B contains A)

### Update Component Quantity

```
PUT /api/v1/products/{product_id}/components/{component_id}
```

### Remove Component

```
DELETE /api/v1/products/{product_id}/components/{component_id}
```

---

## Product Images

Upload and manage product images.

### List Images

```
GET /api/v1/products/{product_id}/images
```

**Response: 200 OK**

```json
{
  "images": [
    {
      "id": "fff66666-e89b-12d3-a456-426614174000",
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "image_url": "/uploads/products/550e8400.../image1.webp",
      "thumbnail_url": "/uploads/products/550e8400.../image1_thumb.webp",
      "alt_text": "Dragon miniature front view",
      "display_order": 0,
      "is_primary": true,
      "original_filename": "dragon-front.jpg",
      "file_size": 245678,
      "content_type": "image/webp",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Upload Image

```
POST /api/v1/products/{product_id}/images
```

**Content-Type:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| file | file | Image file (JPEG, PNG, WebP, max 10MB) |
| alt_text | string | Alt text for accessibility |

First image uploaded becomes primary automatically.

### Update Image Metadata

```
PATCH /api/v1/products/{product_id}/images/{image_id}
```

**Request Body:**

```json
{
  "alt_text": "Updated alt text",
  "display_order": 2
}
```

### Set Primary Image

```
POST /api/v1/products/{product_id}/images/{image_id}/set-primary
```

### Rotate Image

```
POST /api/v1/products/{product_id}/images/{image_id}/rotate?degrees=90
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| degrees | 90, 180, 270 | Clockwise rotation |

### Delete Image

```
DELETE /api/v1/products/{product_id}/images/{image_id}
```

If deleting the primary image, the next image becomes primary.

---

## Code Examples

### Python: Create Product with Models

```python
import httpx

async def create_product(token: str, product_data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.batchivo.app/api/v1/products",
            json={
                "sku": "PROD-NEW",
                "name": "New Product",
                "models": [
                    {"model_id": "model-uuid-here", "quantity": 1}
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### JavaScript: Upload Product Image

```javascript
async function uploadProductImage(productId, file, token) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("alt_text", "Product image");

  const response = await fetch(
    `https://api.batchivo.app/api/v1/products/${productId}/images`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    }
  );
  return response.json();
}
```

### cURL: Add Pricing

```bash
curl -X POST "https://api.batchivo.app/api/v1/products/PRODUCT_ID/pricing" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sales_channel_id": "CHANNEL_ID",
    "list_price": 29.99,
    "is_active": true
  }'
```
