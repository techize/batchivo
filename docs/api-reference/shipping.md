# Shipping API

Calculate shipping rates and validate UK postcodes. Public endpoints for storefront checkout integration.

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/shipping/rates | Get shipping rates for postcode |
| GET | /api/v1/shipping/validate-postcode/{postcode} | Validate UK postcode |
| GET | /api/v1/shipping/methods | List shipping methods |

---

## Get Shipping Rates

Calculate available shipping options for a given postcode and order.

```
POST /api/v1/shipping/rates
```

**Request Body:**

```json
{
  "postcode": "SW1A 1AA",
  "weight_grams": 500,
  "cart_total_pence": 2500
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| postcode | string | Yes | UK postcode |
| weight_grams | integer | No | Total order weight in grams |
| cart_total_pence | integer | No | Cart total in pence |

**Response: 200 OK**

```json
{
  "rates": [
    {
      "id": "royal_mail_24",
      "name": "Royal Mail 24",
      "carrier": "Royal Mail",
      "description": "Next day delivery",
      "price_pence": 395,
      "estimated_days": "1 working day",
      "is_tracked": false,
      "is_signed": false,
      "is_free": false
    },
    {
      "id": "royal_mail_48",
      "name": "Royal Mail 48",
      "carrier": "Royal Mail",
      "description": "2-3 day delivery",
      "price_pence": 295,
      "estimated_days": "2-3 working days",
      "is_tracked": false,
      "is_signed": false,
      "is_free": false
    },
    {
      "id": "royal_mail_tracked_48",
      "name": "Royal Mail Tracked 48",
      "carrier": "Royal Mail",
      "description": "Tracked 2-3 day delivery",
      "price_pence": 450,
      "estimated_days": "2-3 working days",
      "is_tracked": true,
      "is_signed": false,
      "is_free": false
    }
  ],
  "is_highland_island": false,
  "surcharge_applied": false,
  "free_shipping_eligible": false,
  "free_shipping_threshold_pence": 4000
}
```

**Price Notes:**
- All prices are in **pence** (e.g., 395 = £3.95)
- Highland/Island postcodes may have surcharges applied
- Orders over threshold may qualify for free shipping

---

## Validate Postcode

Validate and get details about a UK postcode.

```
GET /api/v1/shipping/validate-postcode/{postcode}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| postcode | string | UK postcode (any format) |

**Response: 200 OK**

```json
{
  "is_valid": true,
  "normalized": "SW1A 1AA",
  "area": "SW",
  "district": "SW1A",
  "region": "London",
  "is_highland_island": false
}
```

**Highland/Island Response:**

```json
{
  "is_valid": true,
  "normalized": "IV1 1AA",
  "area": "IV",
  "district": "IV1",
  "region": "Highland",
  "is_highland_island": true
}
```

**Invalid Postcode:**

```json
{
  "is_valid": false,
  "normalized": null,
  "area": null,
  "district": null,
  "region": null,
  "is_highland_island": false
}
```

---

## List Shipping Methods

Get all available shipping methods without postcode-specific pricing.

```
GET /api/v1/shipping/methods
```

**Response: 200 OK**

```json
{
  "methods": [
    {
      "id": "royal_mail_24",
      "name": "Royal Mail 24",
      "carrier": "Royal Mail",
      "description": "Next day delivery",
      "base_price_pence": 395,
      "estimated_days": "1 working day",
      "is_tracked": false,
      "is_signed": false
    },
    {
      "id": "royal_mail_48",
      "name": "Royal Mail 48",
      "carrier": "Royal Mail",
      "description": "2-3 day delivery",
      "base_price_pence": 295,
      "estimated_days": "2-3 working days",
      "is_tracked": false,
      "is_signed": false
    },
    {
      "id": "royal_mail_tracked_48",
      "name": "Royal Mail Tracked 48",
      "carrier": "Royal Mail",
      "description": "Tracked 2-3 day delivery",
      "base_price_pence": 450,
      "estimated_days": "2-3 working days",
      "is_tracked": true,
      "is_signed": false
    },
    {
      "id": "royal_mail_special_delivery",
      "name": "Royal Mail Special Delivery",
      "carrier": "Royal Mail",
      "description": "Guaranteed next day by 1pm",
      "base_price_pence": 895,
      "estimated_days": "Next day by 1pm",
      "is_tracked": true,
      "is_signed": true
    }
  ],
  "free_shipping_threshold_pence": 4000,
  "highland_island_surcharge_pence": 350
}
```

---

## Highland/Island Areas

The following postcode areas are classified as Highland/Island and may incur surcharges:

| Area | Region |
|------|--------|
| AB30-56 | Aberdeenshire |
| FK17-21 | Stirling/Callander |
| HS | Outer Hebrides |
| IV | Highlands |
| KA27-28 | Isle of Arran |
| KW | Caithness/Orkney |
| PA20-49, PA60-78 | Argyll & Bute |
| PH15-50 | Perth & Kinross |
| ZE | Shetland |
| BT | Northern Ireland |
| IM | Isle of Man |
| JE | Jersey |
| GY | Guernsey |

---

## Code Examples

### Python: Calculate Shipping at Checkout

```python
import httpx

async def get_checkout_shipping(postcode: str, cart_total_pence: int, weight_grams: int):
    async with httpx.AsyncClient() as client:
        # Validate postcode first
        validation = await client.get(
            f"https://api.nozzly.app/api/v1/shipping/validate-postcode/{postcode}"
        )

        if not validation.json()["is_valid"]:
            return {"error": "Invalid postcode"}

        # Get shipping rates
        rates = await client.post(
            "https://api.nozzly.app/api/v1/shipping/rates",
            json={
                "postcode": postcode,
                "weight_grams": weight_grams,
                "cart_total_pence": cart_total_pence
            }
        )

        return rates.json()
```

### JavaScript: Shipping Rate Selector

```javascript
async function getShippingOptions(postcode, cartTotal, weight) {
  const response = await fetch(
    "https://api.nozzly.app/api/v1/shipping/rates",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        postcode: postcode,
        cart_total_pence: cartTotal,
        weight_grams: weight
      })
    }
  );

  const data = await response.json();

  // Format for display
  return data.rates.map(rate => ({
    id: rate.id,
    label: `${rate.name} - £${(rate.price_pence / 100).toFixed(2)}`,
    description: `${rate.estimated_days}${rate.is_tracked ? " (Tracked)" : ""}`,
    price: rate.price_pence,
    isFree: rate.is_free
  }));
}
```

### cURL: Validate Postcode

```bash
curl -X GET "https://api.nozzly.app/api/v1/shipping/validate-postcode/SW1A%201AA"
```

---

## Integration Notes

### Checkout Flow

1. User enters postcode
2. Call `/validate-postcode` to check validity
3. If valid, call `/rates` with cart details
4. Display shipping options to user
5. Include selected shipping in order creation

### Price Calculations

```
Final Price = Base Price + Highland/Island Surcharge (if applicable)

If cart_total >= free_shipping_threshold:
  Final Price = 0 (for standard options)
```

### Caching

- Shipping methods rarely change - cache `/methods` response
- Rates are dynamic - always fetch fresh for checkout
- Postcode validation can be cached per postcode
