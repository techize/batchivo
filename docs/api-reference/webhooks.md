# Webhooks API

Configure webhook subscriptions to receive real-time notifications for events. All endpoints require authentication and are scoped to the current tenant.

## Endpoints Summary

### Subscriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/webhooks/subscriptions | List subscriptions |
| POST | /api/v1/webhooks/subscriptions | Create subscription |
| GET | /api/v1/webhooks/subscriptions/{id} | Get subscription |
| PUT | /api/v1/webhooks/subscriptions/{id} | Update subscription |
| DELETE | /api/v1/webhooks/subscriptions/{id} | Delete subscription |
| POST | /api/v1/webhooks/subscriptions/{id}/regenerate-secret | Regenerate secret |
| POST | /api/v1/webhooks/subscriptions/{id}/test | Test subscription |

### Deliveries
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/webhooks/deliveries | List deliveries |
| GET | /api/v1/webhooks/deliveries/{id} | Get delivery details |
| POST | /api/v1/webhooks/deliveries/{id}/retry | Retry failed delivery |

### Event Types
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/webhooks/event-types | List available events |

---

## Event Types

### List Available Events

Get all webhook event types you can subscribe to.

```
GET /api/v1/webhooks/event-types
```

**Response: 200 OK**

```json
[
  {
    "event_type": "order.created",
    "category": "order",
    "description": "Triggered when a new order is created"
  },
  {
    "event_type": "order.paid",
    "category": "order",
    "description": "Triggered when an order payment is confirmed"
  },
  {
    "event_type": "order.shipped",
    "category": "order",
    "description": "Triggered when an order is marked as shipped"
  }
]
```

### Available Events

| Category | Event | Description |
|----------|-------|-------------|
| **Order** | order.created | New order created |
| | order.paid | Payment confirmed |
| | order.shipped | Order shipped |
| | order.delivered | Order delivered |
| | order.cancelled | Order cancelled |
| **Payment** | payment.completed | Payment processed |
| | payment.refunded | Payment refunded |
| | payment.failed | Payment failed |
| **Inventory** | inventory.low_stock | Stock below threshold |
| | inventory.out_of_stock | Product out of stock |
| | inventory.restocked | Product restocked |
| **Product** | product.created | New product created |
| | product.updated | Product updated |
| | product.deleted | Product deleted |
| **Review** | review.submitted | New review submitted |
| | review.approved | Review approved |
| **Customer** | customer.registered | New customer registered |
| | customer.updated | Customer profile updated |
| **Return** | return.requested | Return request submitted |
| | return.approved | Return approved |
| | return.completed | Return completed |

---

## Subscriptions

### Create Subscription

Create a new webhook subscription.

```
POST /api/v1/webhooks/subscriptions
```

**Request Body:**

```json
{
  "name": "Order Notifications",
  "url": "https://my-server.com/webhooks/nozzly",
  "events": ["order.created", "order.paid", "order.shipped"],
  "custom_headers": {
    "X-Custom-Header": "my-value"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Subscription name |
| url | string | Yes | Webhook endpoint URL (HTTPS required) |
| events | array | Yes | List of event types to subscribe to |
| custom_headers | object | No | Custom headers to include in requests |

**Response: 201 Created**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Order Notifications",
  "url": "https://my-server.com/webhooks/nozzly",
  "events": ["order.created", "order.paid", "order.shipped"],
  "is_active": true,
  "failure_count": 0,
  "last_triggered_at": null,
  "last_success_at": null,
  "custom_headers": {
    "X-Custom-Header": "my-value"
  },
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z",
  "secret": "whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Important:** The `secret` is only returned on creation. Store it securely for signature verification.

### List Subscriptions

```
GET /api/v1/webhooks/subscriptions
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_inactive | boolean | false | Include inactive subscriptions |

**Response: 200 OK**

```json
{
  "subscriptions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Order Notifications",
      "url": "https://my-server.com/webhooks/nozzly",
      "events": ["order.created", "order.paid", "order.shipped"],
      "is_active": true,
      "failure_count": 0,
      "last_triggered_at": "2024-03-15T14:30:00Z",
      "last_success_at": "2024-03-15T14:30:00Z",
      "custom_headers": {},
      "created_at": "2024-03-15T10:30:00Z",
      "updated_at": "2024-03-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Update Subscription

```
PUT /api/v1/webhooks/subscriptions/{subscription_id}
```

**Request Body:**

```json
{
  "name": "All Order Events",
  "events": ["order.created", "order.paid", "order.shipped", "order.delivered"],
  "is_active": true
}
```

### Delete Subscription

```
DELETE /api/v1/webhooks/subscriptions/{subscription_id}
```

**Response: 204 No Content**

Deletes subscription and all delivery history.

### Regenerate Secret

Generate a new signing secret for a subscription.

```
POST /api/v1/webhooks/subscriptions/{subscription_id}/regenerate-secret
```

**Response: 200 OK**

```json
{
  "secret": "whsec_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
}
```

**Warning:** Old secret will no longer work. Update your webhook handler immediately.

### Test Subscription

Send a test webhook to verify configuration.

```
POST /api/v1/webhooks/subscriptions/{subscription_id}/test
```

**Request Body (optional):**

```json
{
  "event_type": "order.created",
  "test_data": {
    "custom": "data"
  }
}
```

**Response: 200 OK**

```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 145,
  "response_body": "OK",
  "error_message": null
}
```

---

## Deliveries

### List Deliveries

View webhook delivery history.

```
GET /api/v1/webhooks/deliveries
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| subscription_id | UUID | - | Filter by subscription |
| event_type | string | - | Filter by event type |
| status | string | - | Filter by status (pending, success, failed) |
| page | integer | 1 | Page number |
| limit | integer | 50 | Items per page (max: 100) |

**Response: 200 OK**

```json
{
  "deliveries": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "order.created",
      "status": "success",
      "status_code": 200,
      "attempt_count": 1,
      "created_at": "2024-03-15T14:30:00Z",
      "delivered_at": "2024-03-15T14:30:01Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

### Get Delivery Details

```
GET /api/v1/webhooks/deliveries/{delivery_id}
```

**Response: 200 OK**

```json
{
  "id": "aaa11111-e89b-12d3-a456-426614174000",
  "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "order.created",
  "status": "success",
  "status_code": 200,
  "attempt_count": 1,
  "request_headers": {
    "Content-Type": "application/json",
    "X-Webhook-Signature": "sha256=..."
  },
  "request_body": "{\"event\":\"order.created\",\"data\":{...}}",
  "response_headers": {
    "Content-Type": "text/plain"
  },
  "response_body": "OK",
  "error_message": null,
  "created_at": "2024-03-15T14:30:00Z",
  "delivered_at": "2024-03-15T14:30:01Z"
}
```

### Retry Failed Delivery

Manually retry a failed webhook delivery.

```
POST /api/v1/webhooks/deliveries/{delivery_id}/retry
```

**Response: 200 OK**

Returns updated delivery with new attempt results.

---

## Webhook Payload Format

All webhooks are delivered as POST requests with JSON body:

```json
{
  "id": "evt_xxxxxxxxxxxxxxxxxxxx",
  "event": "order.created",
  "created_at": "2024-03-15T14:30:00Z",
  "data": {
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "order_number": "MYS-2024-0042",
    "customer_email": "customer@example.com",
    "total": 29.99,
    "currency": "GBP"
  }
}
```

---

## Signature Verification

All webhooks include a signature header for verification:

```
X-Webhook-Signature: sha256=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Verification Example (Python)

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    received = signature.replace("sha256=", "")
    return hmac.compare_digest(expected, received)

# In your webhook handler:
@app.post("/webhooks/nozzly")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Webhook-Signature")

    if not verify_webhook(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(401, "Invalid signature")

    data = json.loads(payload)
    # Process webhook...
```

### Verification Example (JavaScript)

```javascript
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  const received = signature.replace('sha256=', '');
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(received)
  );
}
```

---

## Retry Policy

Failed deliveries are automatically retried with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

After 5 failed attempts, the subscription is marked inactive.

---

## Best Practices

### Endpoint Requirements

1. **HTTPS required** - All webhook URLs must use HTTPS
2. **Fast response** - Return 200 within 30 seconds
3. **Idempotent** - Handle duplicate deliveries gracefully
4. **Verify signatures** - Always verify webhook signatures

### Response Handling

- Return **2xx** status for successful processing
- Return **4xx** for permanent failures (won't retry)
- Return **5xx** for temporary failures (will retry)

### Event Processing

```python
# Example: Process events asynchronously
@app.post("/webhooks/nozzly")
async def handle_webhook(request: Request):
    # 1. Verify signature (do this first)
    # 2. Parse payload
    # 3. Queue for async processing
    # 4. Return 200 immediately

    await queue.enqueue(process_webhook, data)
    return {"status": "received"}
```
